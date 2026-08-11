"""Subprocess harness used by PostgreSQL worker-crash integration tests."""

from __future__ import annotations

import argparse
import asyncio

from pydantic import BaseModel, ConfigDict

from adaptive_rag.db.session import create_engine_from_url, create_session_factory
from adaptive_rag.jobs import JobContext, JobHandlerDefinition, JobRegistry, RetryPolicy
from adaptive_rag.jobs.worker import JobWorker


class FaultPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    value: str


async def _block_forever(
    _context: JobContext, _payload: FaultPayload
) -> dict[str, str]:
    while True:
        await asyncio.sleep(60)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("database_url")
    args = parser.parse_args()
    engine = create_engine_from_url(args.database_url)
    factory = create_session_factory(engine)
    registry = JobRegistry()
    registry.register(
        JobHandlerDefinition(
            name="fault_worker",
            version=1,
            payload_model=FaultPayload,
            handler=_block_forever,
            queue_name="default",
            allowed_scopes=frozenset({"system"}),
            retry_policy=RetryPolicy(
                max_retries=2,
                base_delay_seconds=1,
                max_delay_seconds=1,
            ),
            lease_seconds=15,
        )
    )
    JobWorker(
        session_factory=factory,
        registry=registry,
        queue_names=("default",),
        heartbeat_interval_seconds=60,
    ).run_once_sync()


if __name__ == "__main__":
    main()
