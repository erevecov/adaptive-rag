"""Async general worker with short claim/finalization transactions."""

from __future__ import annotations

import asyncio
import inspect
import os
import socket
from collections.abc import Callable, Collection, Mapping
from contextlib import suppress
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

import psycopg
from sqlalchemy import select
from sqlalchemy.engine import Engine
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
        max_concurrency: int = 1,
        reaper_interval_seconds: float = 15.0,
    ) -> None:
        if heartbeat_interval_seconds <= 0:
            raise ValueError("heartbeat_interval_seconds must be positive")
        if not 1 <= max_concurrency <= 64:
            raise ValueError("max_concurrency must be within [1, 64]")
        if reaper_interval_seconds <= 0:
            raise ValueError("reaper_interval_seconds must be positive")
        self._session_factory = session_factory
        self._registry = registry
        self._queue_names = tuple(queue_names)
        self.worker_id = worker_id or uuid4()
        self._workspace_id = workspace_id
        self._now_source = now_source
        self._heartbeat_interval_seconds = heartbeat_interval_seconds
        self._max_concurrency = max_concurrency
        self._reaper_interval_seconds = reaper_interval_seconds
        self._shutdown_requested = asyncio.Event()

    async def run_once(self) -> WorkerRunReport:
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
            self._invoke_handler(definition=definition, context=context, claim=claim)
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
            return await asyncio.to_thread(self._complete, claim, result)
        finally:
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
        await asyncio.to_thread(self._register_presence)
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
                    await asyncio.to_thread(self._reap_once)
                    next_reaper_at = loop.time() + self._reaper_interval_seconds
                batch_task = asyncio.create_task(self._run_batch_once())
                shutdown_task = asyncio.create_task(self._shutdown_requested.wait())
                done, _pending = await asyncio.wait(
                    {batch_task, shutdown_task},
                    return_when=asyncio.FIRST_COMPLETED,
                )
                if shutdown_task in done and not batch_task.done():
                    await asyncio.to_thread(self._mark_presence_draining)
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
                await asyncio.to_thread(self._heartbeat_presence)
                if self._shutdown_requested.is_set():
                    break
                if all(report.status == "idle" for report in reports):
                    if notification_waiter is not None:
                        await asyncio.to_thread(
                            notification_waiter.wait,
                            timeout_seconds=poll_interval_seconds,
                        )
                    else:
                        try:
                            await asyncio.wait_for(
                                self._shutdown_requested.wait(),
                                timeout=poll_interval_seconds,
                            )
                        except TimeoutError:
                            pass
        finally:
            if notification_waiter is not None:
                await asyncio.to_thread(notification_waiter.close)
            await asyncio.to_thread(self._mark_presence_draining)
            await asyncio.to_thread(self._mark_presence_shutdown)

    async def _run_batch_once(self) -> list[WorkerRunReport]:
        return list(
            await asyncio.gather(
                *(self.run_once() for _index in range(self._max_concurrency))
            )
        )

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
    ) -> object:
        payload = definition.payload_model.model_validate(claim.payload)
        if inspect.iscoroutinefunction(definition.handler):
            return await definition.handler(context, payload)
        result = await asyncio.to_thread(definition.handler, context, payload)
        if inspect.isawaitable(result):
            return await result
        return result

    async def _heartbeat_loop(
        self,
        *,
        claim: ClaimedJob,
        stop: asyncio.Event,
        lost_fence: asyncio.Event,
    ) -> None:
        while not stop.is_set():
            try:
                await asyncio.wait_for(
                    stop.wait(), timeout=self._heartbeat_interval_seconds
                )
                return
            except TimeoutError:
                healthy = await asyncio.to_thread(self._heartbeat_once, claim)
                if not healthy:
                    lost_fence.set()
                    return

    def _claim_and_commit(self) -> ClaimedJob | None:
        with self._session_factory() as session:
            claim = JobDispatcher(
                session=session,
                registry=self._registry,
                queue_names=self._queue_names,
            ).claim_next(
                worker_id=self.worker_id,
                now=self._now_source(),
                workspace_id=self._workspace_id,
            )
            session.commit()
            return claim

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
        with self._session_factory() as session:
            presence = session.get(JobWorkerPresence, self.worker_id)
            if presence is not None and presence.shutdown_at is None:
                presence.heartbeat_at = self._now_source()
            session.commit()

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
        definition = self._registry.get(claim.job_type, claim.handler_version)
        now = self._now_source()
        with self._session_factory() as session:
            healthy = JobRuntimeRepository(session).heartbeat(
                job_id=claim.job_id,
                attempt_id=claim.attempt_id,
                now=now,
                lease_expires_at=now + timedelta(seconds=definition.lease_seconds),
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
            session.commit()
        return self._report(
            claim=claim,
            status="succeeded" if transitioned else "fenced",
            result=result if transitioned else None,
        )

    def _finalize_error(self, claim: ClaimedJob, error: Exception) -> WorkerRunReport:
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
                )
                status = "blocked"
            elif isinstance(error, PermanentJobError):
                transitioned = transitions.dead_letter(
                    job_id=claim.job_id,
                    attempt_id=claim.attempt_id,
                    reason=error,
                    now=self._now_source(),
                    error_code=error.code,
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
            error_message=str(error) or error.__class__.__name__,
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
