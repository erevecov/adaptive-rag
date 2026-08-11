"""Async general worker with short claim/finalization transactions."""

from __future__ import annotations

import asyncio
import inspect
import logging
import os
import socket
from collections.abc import Callable, Collection, Mapping
from contextlib import suppress
from contextvars import copy_context
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from threading import BoundedSemaphore, Lock, Thread
from time import sleep
from typing import Any
from uuid import UUID, uuid4

import psycopg
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from adaptive_rag.db.models import Job
from adaptive_rag.db.models import JobWorker as JobWorkerPresence
from adaptive_rag.db.repositories.job_runtime import JobRuntimeRepository
from adaptive_rag.jobs.dispatcher import ClaimedJob, JobDispatcher
from adaptive_rag.jobs.errors import (
    BlockedJobError,
    JobCancelled,
    PermanentJobError,
    RetryableJobError,
)
from adaptive_rag.jobs.reaper import JobReaper
from adaptive_rag.jobs.registry import JobHandlerDefinition, JobRegistry
from adaptive_rag.jobs.transitions import JobTransitions
from adaptive_rag.jobs.types import JobContext

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class WorkerRunReport:
    status: str
    worker_id: UUID
    job_id: UUID | None = None
    attempt_id: UUID | None = None
    job_type: str | None = None
    workspace_id: UUID | None = None
    result: object | None = None
    error_code: str | None = None
    error_message: str | None = None


class PostgresNotificationWaiter:
    """Dedicated autocommit LISTEN connection with polling-compatible timeout."""

    channel = "adaptive_rag_jobs"

    def __init__(self, *, database_url: str) -> None:
        self._database_url = database_url.replace(
            "postgresql+psycopg://", "postgresql://", 1
        )
        self._connection: psycopg.Connection[Any] | None = None

    @classmethod
    def from_session_factory(
        cls, factory: sessionmaker[Session]
    ) -> PostgresNotificationWaiter:
        bind = factory.kw.get("bind")
        if not isinstance(bind, Engine) or bind.dialect.name != "postgresql":
            raise ValueError("PostgreSQL notification waiting requires a PG engine")
        return cls(database_url=bind.url.render_as_string(hide_password=False))

    def open(self) -> None:
        if self._connection is not None:
            return
        self._connection = psycopg.connect(self._database_url, autocommit=True)
        self._connection.execute(f"LISTEN {self.channel}")

    def wait(self, *, timeout_seconds: float) -> bool:
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        if self._connection is None:
            raise RuntimeError("notification waiter is not open")
        notification = next(
            self._connection.notifies(timeout=timeout_seconds, stop_after=1),
            None,
        )
        return notification is not None

    def close(self) -> None:
        if self._connection is not None:
            self._connection.close()
            self._connection = None


class _ExecutionCapacityLease:
    """Hold one local slot until both coroutine and detached thread are done."""

    def __init__(self, capacity: BoundedSemaphore) -> None:
        self._capacity = capacity
        self._lock = Lock()
        self._coroutine_done = False
        self._thread_started = False
        self._thread_done = False
        self._released = False

    def mark_thread_started(self) -> None:
        with self._lock:
            self._thread_started = True

    def mark_thread_done(self) -> None:
        with self._lock:
            self._thread_done = True
            self._release_if_done()

    def mark_coroutine_done(self) -> None:
        with self._lock:
            self._coroutine_done = True
            self._release_if_done()

    def _release_if_done(self) -> None:
        if self._released or not self._coroutine_done:
            return
        if self._thread_started and not self._thread_done:
            return
        self._released = True
        self._capacity.release()


class JobWorker:
    """Claims durably, runs one typed handler, then finalizes through a fence."""

    def __init__(
        self,
        *,
        session_factory: sessionmaker[Session],
        registry: JobRegistry,
        queue_names: Collection[str],
        worker_id: UUID | None = None,
        workspace_id: UUID | None = None,
        now_source: Callable[[], datetime] = lambda: datetime.now(UTC),
        heartbeat_interval_seconds: float = 30.0,
        presence_heartbeat_interval_seconds: float = 10.0,
        presence_retry_delay_seconds: float = 0.1,
        max_concurrency: int = 1,
        reaper_interval_seconds: float = 15.0,
    ) -> None:
        if heartbeat_interval_seconds <= 0:
            raise ValueError("heartbeat_interval_seconds must be positive")
        if presence_heartbeat_interval_seconds <= 0:
            raise ValueError(
                "presence_heartbeat_interval_seconds must be positive"
            )
        if not 0 <= presence_retry_delay_seconds <= 5:
            raise ValueError("presence_retry_delay_seconds must be within [0, 5]")
        if not 1 <= max_concurrency <= 64:
            raise ValueError("max_concurrency must be within [1, 64]")
        if reaper_interval_seconds <= 0:
            raise ValueError("reaper_interval_seconds must be positive")
        self._session_factory = session_factory
        self._registry = registry
        self._queue_names = tuple(dict.fromkeys(queue_names))
        self.worker_id = worker_id or uuid4()
        self._workspace_id = workspace_id
        self._now_source = now_source
        self._heartbeat_interval_seconds = heartbeat_interval_seconds
        self._presence_heartbeat_interval_seconds = (
            presence_heartbeat_interval_seconds
        )
        self._presence_retry_delay_seconds = presence_retry_delay_seconds
        self._max_concurrency = max_concurrency
        self._execution_capacity = BoundedSemaphore(max_concurrency)
        self._reaper_interval_seconds = reaper_interval_seconds
        self._shutdown_requested = asyncio.Event()
        self._queue_rotation_lock = Lock()
        self._next_queue_index = 0

    async def run_once(self) -> WorkerRunReport:
        if not self._execution_capacity.acquire(blocking=False):
            return WorkerRunReport(status="local_capacity", worker_id=self.worker_id)
        capacity_lease = _ExecutionCapacityLease(self._execution_capacity)
        try:
            return await self._run_once_with_capacity(capacity_lease=capacity_lease)
        finally:
            capacity_lease.mark_coroutine_done()

    async def _run_once_with_capacity(
        self,
        *,
        capacity_lease: _ExecutionCapacityLease,
    ) -> WorkerRunReport:
        claim = await asyncio.to_thread(self._claim_and_commit)
        if claim is None:
            return WorkerRunReport(status="idle", worker_id=self.worker_id)
        definition = self._registry.get(claim.job_type, claim.handler_version)
        lease_healthy = True
        stop_heartbeat = asyncio.Event()
        lost_fence = asyncio.Event()

        def is_lease_healthy() -> bool:
            return lease_healthy and not lost_fence.is_set()

        context = JobContext(
            job_id=claim.job_id,
            attempt_id=claim.attempt_id,
            workspace_id=claim.workspace_id,
            idempotency_key=claim.idempotency_key,
            is_cancel_requested_callback=lambda: self._is_cancel_requested(claim),
            report_progress_callback=lambda progress: self._report_progress(
                claim, progress
            ),
            is_lease_healthy_callback=is_lease_healthy,
        )
        heartbeat_task = asyncio.create_task(
            self._heartbeat_loop(
                claim=claim,
                stop=stop_heartbeat,
                lost_fence=lost_fence,
            )
        )
        handler_task = asyncio.create_task(
            self._invoke_handler(
                definition=definition,
                context=context,
                claim=claim,
                capacity_lease=capacity_lease,
            )
        )
        fence_task = asyncio.create_task(lost_fence.wait())
        try:
            done, _pending = await asyncio.wait(
                {handler_task, fence_task},
                return_when=asyncio.FIRST_COMPLETED,
            )
            if fence_task in done and lost_fence.is_set() and not handler_task.done():
                lease_healthy = False
                handler_task.cancel()
                with suppress(asyncio.CancelledError):
                    await handler_task
                return self._report(claim=claim, status="fenced")
            fence_task.cancel()
            with suppress(asyncio.CancelledError):
                await fence_task
            try:
                result = await handler_task
            except asyncio.CancelledError:
                raise
            except Exception as exc:  # noqa: BLE001 - classified below
                return await asyncio.to_thread(self._finalize_error, claim, exc)
            if not is_lease_healthy():
                return self._report(claim=claim, status="fenced")
            try:
                return await asyncio.to_thread(self._complete, claim, result)
            except Exception as exc:  # noqa: BLE001 - finalized below
                return await asyncio.to_thread(self._finalize_error, claim, exc)
        except asyncio.CancelledError:
            lease_healthy = False
            lost_fence.set()
            raise
        finally:
            if not handler_task.done():
                handler_task.cancel()
                with suppress(asyncio.CancelledError):
                    await handler_task
            stop_heartbeat.set()
            heartbeat_task.cancel()
            with suppress(asyncio.CancelledError):
                await heartbeat_task

    def run_once_sync(self) -> WorkerRunReport:
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(self.run_once())
        raise RuntimeError("run_once_sync cannot run inside an active event loop")

    async def run(
        self,
        *,
        poll_interval_seconds: float = 5.0,
        drain_timeout_seconds: float = 30.0,
    ) -> None:
        if poll_interval_seconds <= 0:
            raise ValueError("poll_interval_seconds must be positive")
        if drain_timeout_seconds < 0:
            raise ValueError("drain_timeout_seconds must be non-negative")
        await asyncio.to_thread(
            self._write_presence_best_effort,
            "registration",
            self._register_presence,
        )
        presence_stop = asyncio.Event()
        presence_task = asyncio.create_task(
            self._presence_heartbeat_loop(stop=presence_stop)
        )
        notification_waiter = self._create_notification_waiter()
        if notification_waiter is not None:
            try:
                await asyncio.to_thread(notification_waiter.open)
            except (OSError, psycopg.Error):
                notification_waiter = None
        loop = asyncio.get_running_loop()
        next_reaper_at = 0.0
        try:
            while not self._shutdown_requested.is_set():
                if loop.time() >= next_reaper_at:
                    try:
                        await asyncio.to_thread(self._reap_once)
                    except (SQLAlchemyError, psycopg.Error, OSError):
                        logger.exception("job reaper database operation failed")
                    next_reaper_at = loop.time() + self._reaper_interval_seconds
                batch_task = asyncio.create_task(self._run_batch_once())
                shutdown_task = asyncio.create_task(self._shutdown_requested.wait())
                done, _pending = await asyncio.wait(
                    {batch_task, shutdown_task},
                    return_when=asyncio.FIRST_COMPLETED,
                )
                if shutdown_task in done and not batch_task.done():
                    await asyncio.to_thread(
                        self._write_presence_best_effort,
                        "draining",
                        self._mark_presence_draining,
                    )
                    try:
                        reports = await asyncio.wait_for(
                            asyncio.shield(batch_task),
                            timeout=drain_timeout_seconds,
                        )
                    except TimeoutError:
                        batch_task.cancel()
                        with suppress(asyncio.CancelledError):
                            await batch_task
                        break
                else:
                    reports = await batch_task
                shutdown_task.cancel()
                with suppress(asyncio.CancelledError):
                    await shutdown_task
                await asyncio.to_thread(
                    self._write_presence_best_effort,
                    "heartbeat",
                    self._heartbeat_presence,
                )
                if self._shutdown_requested.is_set():
                    break
                if all(
                    report.status in {"idle", "local_capacity", "worker_error"}
                    for report in reports
                ):
                    if notification_waiter is not None:
                        try:
                            await asyncio.to_thread(
                                notification_waiter.wait,
                                timeout_seconds=poll_interval_seconds,
                            )
                        except (OSError, psycopg.Error):
                            logger.warning(
                                "job notification connection failed; using polling",
                                exc_info=True,
                            )
                            with suppress(OSError, psycopg.Error):
                                await asyncio.to_thread(notification_waiter.close)
                            notification_waiter = None
                    else:
                        try:
                            await asyncio.wait_for(
                                self._shutdown_requested.wait(),
                                timeout=poll_interval_seconds,
                            )
                        except TimeoutError:
                            pass
        finally:
            presence_stop.set()
            presence_task.cancel()
            with suppress(asyncio.CancelledError):
                await presence_task
            if notification_waiter is not None:
                with suppress(OSError, psycopg.Error):
                    await asyncio.to_thread(notification_waiter.close)
            await asyncio.to_thread(
                self._write_presence_best_effort,
                "draining",
                self._mark_presence_draining,
            )
            await asyncio.to_thread(
                self._write_presence_best_effort,
                "shutdown",
                self._mark_presence_shutdown,
            )

    async def _run_batch_once(self) -> list[WorkerRunReport]:
        return list(
            await asyncio.gather(
                *(self._run_slot_once() for _index in range(self._max_concurrency))
            )
        )

    async def _run_slot_once(self) -> WorkerRunReport:
        try:
            return await self.run_once()
        except Exception:  # noqa: BLE001 - one slot must not terminate the daemon
            logger.exception("job worker slot failed")
            return WorkerRunReport(status="worker_error", worker_id=self.worker_id)

    def request_shutdown(self) -> None:
        self._shutdown_requested.set()

    def _create_notification_waiter(self) -> PostgresNotificationWaiter | None:
        bind = self._session_factory.kw.get("bind")
        if not isinstance(bind, Engine) or bind.dialect.name != "postgresql":
            return None
        return PostgresNotificationWaiter.from_session_factory(self._session_factory)

    async def _invoke_handler(
        self,
        *,
        definition: JobHandlerDefinition,
        context: JobContext,
        claim: ClaimedJob,
        capacity_lease: _ExecutionCapacityLease,
    ) -> object:
        payload = definition.payload_model.model_validate(claim.payload)
        if inspect.iscoroutinefunction(definition.handler):
            return await definition.handler(context, payload)
        result = await self._invoke_sync_handler(
            definition=definition,
            context=context,
            payload=payload,
            capacity_lease=capacity_lease,
        )
        if inspect.isawaitable(result):
            return await result
        return result

    async def _invoke_sync_handler(
        self,
        *,
        definition: JobHandlerDefinition,
        context: JobContext,
        payload: BaseModel,
        capacity_lease: _ExecutionCapacityLease,
    ) -> object:
        """Run sync work on a daemon thread so drain timeout bounds process exit."""

        loop = asyncio.get_running_loop()
        future: asyncio.Future[object] = loop.create_future()
        caller_context = copy_context()

        def deliver_result(result: object) -> None:
            if not future.done():
                future.set_result(result)

        def deliver_error(error: BaseException) -> None:
            if not future.done():
                future.set_exception(error)

        def notify(callback: Callable[..., None], *args: object) -> None:
            try:
                loop.call_soon_threadsafe(callback, *args)
            except RuntimeError:
                # The shutdown path may close the loop before detached work returns.
                pass

        def invoke() -> None:
            try:
                result = caller_context.run(definition.handler, context, payload)
            except BaseException as exc:  # noqa: BLE001 - deliver into event loop
                if isinstance(exc, StopIteration):
                    exc = RuntimeError("synchronous job handler raised StopIteration")
                if not loop.is_closed():
                    notify(deliver_error, exc)
            else:
                if not loop.is_closed():
                    notify(deliver_result, result)
            finally:
                capacity_lease.mark_thread_done()

        thread = Thread(
            target=invoke,
            name=f"job-{definition.name}-{context.job_id}",
            daemon=True,
        )
        capacity_lease.mark_thread_started()
        try:
            thread.start()
        except BaseException:
            capacity_lease.mark_thread_done()
            raise
        return await future

    async def _heartbeat_loop(
        self,
        *,
        claim: ClaimedJob,
        stop: asyncio.Event,
        lost_fence: asyncio.Event,
    ) -> None:
        interval = self._attempt_heartbeat_interval(claim.lease_seconds)
        while not stop.is_set():
            try:
                await asyncio.wait_for(stop.wait(), timeout=interval)
                return
            except TimeoutError:
                try:
                    healthy = await asyncio.to_thread(self._heartbeat_once, claim)
                except (SQLAlchemyError, psycopg.Error, OSError):
                    logger.exception(
                        "job attempt heartbeat failed; fencing local execution"
                    )
                    lost_fence.set()
                    return
                if not healthy:
                    lost_fence.set()
                    return

    def _attempt_heartbeat_interval(self, lease_seconds: int) -> float:
        return min(
            self._heartbeat_interval_seconds,
            max(1.0, lease_seconds / 3),
        )

    async def _presence_heartbeat_loop(self, *, stop: asyncio.Event) -> None:
        while not stop.is_set():
            try:
                await asyncio.wait_for(
                    stop.wait(), timeout=self._presence_heartbeat_interval_seconds
                )
                return
            except TimeoutError:
                await asyncio.to_thread(
                    self._write_presence_best_effort,
                    "heartbeat",
                    self._heartbeat_presence,
                )

    def _write_presence_best_effort(
        self,
        operation_name: str,
        operation: Callable[[], None],
    ) -> bool:
        for attempt in range(1, 4):
            try:
                operation()
                return True
            except (SQLAlchemyError, psycopg.Error, OSError):
                logger.warning(
                    "worker presence %s failed attempt=%s",
                    operation_name,
                    attempt,
                    exc_info=True,
                )
                if attempt < 3 and self._presence_retry_delay_seconds > 0:
                    sleep(self._presence_retry_delay_seconds * (2 ** (attempt - 1)))
        return False

    def _claim_and_commit(self) -> ClaimedJob | None:
        # Claim at most one queue per transaction. Rotating transactions retain
        # fairness without ever acquiring queue rows in conflicting orders.
        queue_names = self._rotated_queue_names()[:1]
        with self._session_factory() as session:
            claim = JobDispatcher(
                session=session,
                registry=self._registry,
                queue_names=queue_names,
            ).claim_next(
                worker_id=self.worker_id,
                now=self._now_source(),
                workspace_id=self._workspace_id,
            )
            session.commit()
            return claim

    def _rotated_queue_names(self) -> tuple[str, ...]:
        if not self._queue_names:
            return ()
        with self._queue_rotation_lock:
            start = self._next_queue_index % len(self._queue_names)
            self._next_queue_index = (start + 1) % len(self._queue_names)
        return self._queue_names[start:] + self._queue_names[:start]

    def _register_presence(self) -> None:
        now = self._now_source()
        with self._session_factory() as session:
            presence = session.get(JobWorkerPresence, self.worker_id)
            if presence is None:
                presence = JobWorkerPresence(
                    id=self.worker_id,
                    process_identity=(f"{socket.gethostname()}:{os.getpid()}"[:128]),
                    application_version="adaptive-rag",
                    supported_queues=list(self._queue_names),
                    supported_handlers=[
                        f"{name}@{version}"
                        for name, version in sorted(self._registry.supported_handlers)
                    ],
                    max_concurrency=self._max_concurrency,
                    started_at=now,
                    heartbeat_at=now,
                )
                session.add(presence)
            else:
                presence.heartbeat_at = now
                presence.draining_at = None
                presence.shutdown_at = None
                presence.max_concurrency = self._max_concurrency
            session.commit()

    def _heartbeat_presence(self) -> None:
        # Upsert rather than update-only so a worker that started during a
        # transient database outage becomes routable after recovery.
        self._register_presence()

    def _mark_presence_draining(self) -> None:
        with self._session_factory() as session:
            presence = session.get(JobWorkerPresence, self.worker_id)
            if presence is not None and presence.draining_at is None:
                presence.draining_at = self._now_source()
                presence.heartbeat_at = self._now_source()
            session.commit()

    def _mark_presence_shutdown(self) -> None:
        with self._session_factory() as session:
            presence = session.get(JobWorkerPresence, self.worker_id)
            if presence is not None:
                presence.shutdown_at = self._now_source()
                presence.heartbeat_at = self._now_source()
            session.commit()

    def _heartbeat_once(self, claim: ClaimedJob) -> bool:
        now = self._now_source()
        with self._session_factory() as session:
            healthy = JobRuntimeRepository(session).heartbeat(
                job_id=claim.job_id,
                attempt_id=claim.attempt_id,
                now=now,
                lease_expires_at=now + timedelta(seconds=claim.lease_seconds),
            )
            session.commit()
            return healthy

    def _reap_once(self) -> int:
        with self._session_factory() as session:
            reaped = JobReaper(session=session, registry=self._registry).run_once(
                now=self._now_source(),
                batch_size=100,
            )
            session.commit()
            return reaped

    def _is_cancel_requested(self, claim: ClaimedJob) -> bool:
        with self._session_factory() as session:
            requested = session.scalar(
                select(Job.cancellation_requested_at).where(
                    Job.id == claim.job_id,
                    Job.status == "running",
                    Job.current_attempt_id == claim.attempt_id,
                )
            )
            return requested is not None

    def _report_progress(
        self, claim: ClaimedJob, progress: Mapping[str, object]
    ) -> None:
        with self._session_factory() as session:
            JobRuntimeRepository(session).update_progress(
                job_id=claim.job_id,
                attempt_id=claim.attempt_id,
                progress=progress,
                now=self._now_source(),
            )
            session.commit()

    def _complete(self, claim: ClaimedJob, result: object) -> WorkerRunReport:
        persisted_result: object | None = None
        with self._session_factory() as session:
            transitioned = JobTransitions(
                session=session,
                registry=self._registry,
            ).complete(
                job_id=claim.job_id,
                attempt_id=claim.attempt_id,
                result=result,
                now=self._now_source(),
            )
            if transitioned:
                job = session.get(Job, claim.job_id)
                if job is not None:
                    persisted_result = job.result_json
            session.commit()
        return self._report(
            claim=claim,
            status="succeeded" if transitioned else "fenced",
            result=persisted_result,
        )

    def _finalize_error(self, claim: ClaimedJob, error: Exception) -> WorkerRunReport:
        trace_id = uuid4().hex
        definition = self._registry.get(claim.job_type, claim.handler_version)
        safe_message = str(definition.redact_error(error))
        logger.exception(
            "job handler failed trace_id=%s job_id=%s attempt_id=%s",
            trace_id,
            claim.job_id,
            claim.attempt_id,
            exc_info=(type(error), error, error.__traceback__),
        )
        with self._session_factory() as session:
            transitions = JobTransitions(session=session, registry=self._registry)
            if isinstance(error, JobCancelled):
                transitioned = transitions.confirm_cancelled(
                    job_id=claim.job_id,
                    attempt_id=claim.attempt_id,
                    now=self._now_source(),
                )
                status = "cancelled"
            elif isinstance(error, BlockedJobError):
                transitioned = transitions.block(
                    job_id=claim.job_id,
                    attempt_id=claim.attempt_id,
                    reason=error,
                    now=self._now_source(),
                    error_code=error.code,
                    trace_id=trace_id,
                )
                status = "blocked"
            elif isinstance(error, PermanentJobError):
                transitioned = transitions.dead_letter(
                    job_id=claim.job_id,
                    attempt_id=claim.attempt_id,
                    reason=error,
                    now=self._now_source(),
                    error_code=error.code,
                    trace_id=trace_id,
                )
                status = "dead_letter"
            else:
                error_code = (
                    error.code
                    if isinstance(error, RetryableJobError)
                    else "unexpected_handler_error"
                )
                transitioned = transitions.retryable_failure(
                    job_id=claim.job_id,
                    attempt_id=claim.attempt_id,
                    error=error,
                    now=self._now_source(),
                    error_code=error_code,
                    trace_id=trace_id,
                )
                job = session.get(Job, claim.job_id)
                if job is None:
                    status = "fenced"
                else:
                    status = "retry_scheduled" if job.status == "queued" else job.status
            session.commit()
        return self._report(
            claim=claim,
            status=status if transitioned else "fenced",
            error_code=getattr(error, "code", error.__class__.__name__),
            error_message=safe_message,
        )

    def _report(
        self,
        *,
        claim: ClaimedJob,
        status: str,
        result: object | None = None,
        error_code: str | None = None,
        error_message: str | None = None,
    ) -> WorkerRunReport:
        return WorkerRunReport(
            status=status,
            worker_id=self.worker_id,
            job_id=claim.job_id,
            attempt_id=claim.attempt_id,
            job_type=claim.job_type,
            workspace_id=claim.workspace_id,
            result=result,
            error_code=error_code,
            error_message=error_message,
        )


__all__ = ["JobWorker", "PostgresNotificationWaiter", "WorkerRunReport"]
