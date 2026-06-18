"""Fixtures de integracion para Postgres + pgvector via testcontainers."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from sqlalchemy import Engine, create_engine, text
from testcontainers.postgres import PostgresContainer

# Imagen con la extension vector preinstalada.
PGVECTOR_IMAGE = "pgvector/pgvector:pg16"


@pytest.fixture(scope="module")
def pg_url() -> Iterator[str]:
    """URL de conexion cruda (con credenciales) al contenedor pgvector."""
    with PostgresContainer(PGVECTOR_IMAGE, driver="psycopg") as pg:
        yield pg.get_connection_url()


@pytest.fixture(scope="module")
def pg_engine(pg_url: str) -> Iterator[Engine]:
    """Engine sobre el contenedor; crea la extension vector al arrancar."""
    engine = create_engine(pg_url)
    with engine.begin() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
    yield engine
    engine.dispose()
