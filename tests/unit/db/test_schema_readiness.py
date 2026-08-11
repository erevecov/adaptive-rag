"""Database readiness fails closed on missing or stale revisions."""

import pytest
from sqlalchemy import create_engine, text

from adaptive_rag.db.schema_readiness import (
    REQUIRED_DATABASE_CAPABILITIES,
    REQUIRED_DATABASE_REVISION,
    assert_database_schema_current,
)


def _install_capabilities(engine, *, revision: str) -> None:  # type: ignore[no-untyped-def]
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE alembic_version (version_num TEXT)"))
        connection.execute(
            text("INSERT INTO alembic_version VALUES (:revision)"),
            {"revision": revision},
        )
        for table_name, columns in REQUIRED_DATABASE_CAPABILITIES.items():
            rendered_columns = ", ".join(f"{column} TEXT" for column in columns)
            connection.execute(
                text(f"CREATE TABLE {table_name} ({rendered_columns})")
            )


def test_schema_readiness_rejects_an_uninitialized_database() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")

    with pytest.raises(RuntimeError, match="not initialized"):
        assert_database_schema_current(engine)


def test_schema_readiness_accepts_only_the_required_revision() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    _install_capabilities(engine, revision=REQUIRED_DATABASE_REVISION)

    assert_database_schema_current(engine)

    with engine.begin() as connection:
        connection.execute(
            text("UPDATE alembic_version SET version_num = 'older_revision'")
        )
        connection.execute(text("DROP TABLE job_attempts"))
    with pytest.raises(RuntimeError, match="missing required database capabilities"):
        assert_database_schema_current(engine)


def test_schema_readiness_accepts_a_newer_unknown_revision_with_capabilities() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    _install_capabilities(engine, revision="future_additive_revision")

    assert_database_schema_current(engine)
