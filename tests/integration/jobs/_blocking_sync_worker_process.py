"""Process fixture proving SIGTERM bounds synchronous handler drain time."""

from __future__ import annotations

import asyncio
import signal
import sys
import time

from pydantic import BaseModel, ConfigDict
from sqlalchemy import create_engine

from adaptive_rag.db.session import create_session_factory
from adaptive_rag.jobs import JobHandlerDefinition, JobRegistry
from adaptive_rag.jobs.worker import JobWorker


class BlockingPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    value: str


def main() -> int:
    database_url = sys.argv[1]
    engine = create_engine(database_url, pool_pre_ping=True)
    factory = create_session_factory(engine)
    registry = JobRegistry()

    def block_forever(_context, _payload: BlockingPayload) -> object:
        while True:
            time.sleep(1)

    registry.register(
        JobHandlerDefinition(
            name="blocking_sync_shutdown",
            version=1,
            payload_model=BlockingPayload,
            handler=block_forever,
            queue_name="default",
            allowed_scopes=frozenset({"system"}),
            lease_seconds=15,
        )
    )
    worker = JobWorker(
        session_factory=factory,
        registry=registry,
        queue_names=("default",),
        presence_heartbeat_interval_seconds=0.1,
    )

    async def run() -> None:
        loop = asyncio.get_running_loop()
        for signum in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(signum, worker.request_shutdown)
        await worker.run(
            poll_interval_seconds=0.05,
            drain_timeout_seconds=0.2,
        )

    try:
        asyncio.run(run())
    finally:
        engine.dispose()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
