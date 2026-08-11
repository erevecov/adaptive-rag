"""Fair multi-queue dispatcher backed by PostgreSQL row and advisory locks."""

from __future__ import annotations

from collections.abc import Collection
from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from adaptive_rag.db.repositories.job_runtime import (
    JobRuntimeRepository,
    RuntimeHandlerConfig,
)
from adaptive_rag.jobs.errors import UnknownJobHandlerError
from adaptive_rag.jobs.registry import JobHandlerDefinition, JobRegistry
from adaptive_rag.jobs.types import HandlerKey


def advisory_lock_id(namespace: str, *parts: str) -> int:
    document = "\x1f".join((namespace, *parts)).encode("utf-8")
    return int.from_bytes(sha256(document).digest()[:8], "big", signed=True)


@dataclass(frozen=True, slots=True)
class ClaimedJob:
    job_id: UUID
    attempt_id: UUID
    worker_id: UUID
    scope: str
    workspace_id: UUID | None
    queue_name: str
    job_type: str
    handler_version: int
    payload: dict[str, Any]
    idempotency_key: str | None
    retry_count: int
    max_retries: int
    lease_expires_at: datetime


class JobDispatcher:
    """Rotates queue preference while PostgreSQL serializes each admission."""

    def __init__(
        self,
        *,
        session: Session,
        registry: JobRegistry,
        queue_names: Collection[str],
    ) -> None:
        self._repository = JobRuntimeRepository(session)
        self._registry = registry
        self._queue_names = tuple(dict.fromkeys(queue_names))
        self._next_queue_index = 0

    def claim_next(
        self,
        *,
        worker_id: UUID,
        now: datetime,
        supported_handlers: Collection[HandlerKey] | None = None,
        queue_names: Collection[str] | None = None,
        workspace_id: UUID | None = None,
    ) -> ClaimedJob | None:
        supported = (
            self._registry.supported_handlers
            if supported_handlers is None
            else frozenset(supported_handlers)
        )
        names = (
            self._queue_names
            if queue_names is None
            else tuple(dict.fromkeys(queue_names))
        )
        if not names or not supported:
            return None
        configs = {
            key: RuntimeHandlerConfig(
                lease_seconds=definition.lease_seconds,
                handler_limit=definition.concurrency.handler_limit,
                key_limit=definition.concurrency.key_limit,
            )
            for key in supported
            if (definition := self._definition_or_none(key)) is not None
        }
        if not configs:
            return None
        start = self._next_queue_index % len(names)
        self._next_queue_index = (start + 1) % len(names)
        ordered_names = names[start:] + names[:start]
        handler_lock_ids = {
            key: advisory_lock_id("handler", key[0], str(key[1])) for key in configs
        }
        for queue_name in ordered_names:
            claim = self._repository.claim_from_queue(
                queue_name=queue_name,
                worker_id=worker_id,
                handler_configs=configs,
                advisory_lock_ids=handler_lock_ids,
                key_lock_id_factory=lambda *parts: advisory_lock_id("key", *parts),
                now=now,
                workspace_id=workspace_id,
            )
            if claim is None:
                continue
            payload_model = self._registry.validate_payload(
                claim.job_type,
                claim.handler_version,
                claim.payload_json,
            )
            return ClaimedJob(
                job_id=claim.job_id,
                attempt_id=claim.attempt_id,
                worker_id=claim.worker_id,
                scope=claim.scope,
                workspace_id=claim.workspace_id,
                queue_name=claim.queue_name,
                job_type=claim.job_type,
                handler_version=claim.handler_version,
                payload=payload_model.model_dump(mode="json"),
                idempotency_key=claim.idempotency_key,
                retry_count=claim.retry_count,
                max_retries=claim.max_retries,
                lease_expires_at=claim.lease_expires_at,
            )
        return None

    def _definition_or_none(self, key: HandlerKey) -> JobHandlerDefinition | None:
        try:
            return self._registry.get(*key)
        except UnknownJobHandlerError:
            return None


__all__ = ["ClaimedJob", "JobDispatcher", "advisory_lock_id"]
