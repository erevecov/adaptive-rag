"""PostgreSQL fixtures for the job-platform integration suite."""

from __future__ import annotations

import os
import subprocess
from collections.abc import Iterator
from pathlib import Path

import pytest
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker
from testcontainers.postgres import PostgresContainer

REPO_ROOT = Path(__file__).resolve().parents[3]
PGVECTOR_IMAGE = "pgvector/pgvector:pg16"


@pytest.fixture(scope="module")
def job_database_url() -> Iterator[str]:
    with PostgresContainer(PGVECTOR_IMAGE, driver="psycopg") as postgres:
        database_url = postgres.get_connection_url()
        result = subprocess.run(
            ["uv", "run", "alembic", "upgrade", "head"],
            cwd=REPO_ROOT,
            env={**os.environ, "ADAPTIVE_RAG_DATABASE_URL": database_url},
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise AssertionError(
                "alembic upgrade head failed\n"
                f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
            )
        yield database_url


@pytest.fixture(scope="module")
def job_engine(job_database_url: str) -> Iterator[Engine]:
    engine = create_engine(job_database_url, pool_pre_ping=True)
    yield engine
    engine.dispose()


@pytest.fixture(scope="module")
def job_session_factory(job_engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(
        bind=job_engine,
        autoflush=False,
        expire_on_commit=False,
    )
