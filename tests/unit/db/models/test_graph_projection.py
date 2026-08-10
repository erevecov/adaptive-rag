"""Tests para el estado Postgres de proyeccion graph por proyecto."""

from __future__ import annotations

from sqlalchemy.exc import IntegrityError

from adaptive_rag.db.base import Base
from adaptive_rag.db.models import Graphprojection, Workspace
from adaptive_rag.db.session import create_engine_from_url, create_session_factory


def _make_session():
    engine = create_engine_from_url("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(
        engine,
        tables=[Workspace.__table__, Graphprojection.__table__],
    )
    return create_session_factory(engine)()


def test_graph_projection_defaults_to_disabled_neo4j_projection() -> None:
    session = _make_session()
    workspace = Workspace(name="demo")
    session.add(workspace)
    session.flush()
    projection = Graphprojection(workspace_id=workspace.id)
    session.add(projection)
    session.commit()

    assert projection.backend == "neo4j"
    assert projection.status == "disabled"
    assert projection.schema_version == "graph-store-v1"
    assert projection.extractor_version == "graph-extractor-v1"
    assert projection.source_watermark is None
    assert projection.last_indexed_at is None


def test_graph_projection_rejects_invalid_status() -> None:
    session = _make_session()
    workspace = Workspace(name="demo")
    session.add(workspace)
    session.flush()
    projection = Graphprojection(workspace_id=workspace.id, status="invalid")

    try:
        session.add(projection)
        session.commit()
    except IntegrityError:
        return
    finally:
        session.rollback()

    raise AssertionError("Expected IntegrityError for invalid graph projection status")


def test_graph_projection_is_unique_per_workspace_and_backend() -> None:
    session = _make_session()
    workspace = Workspace(name="demo")
    session.add(workspace)
    session.flush()
    session.add(Graphprojection(workspace_id=workspace.id, backend="neo4j"))
    session.add(Graphprojection(workspace_id=workspace.id, backend="neo4j"))

    try:
        session.commit()
    except IntegrityError:
        return
    finally:
        session.rollback()

    raise AssertionError("Expected IntegrityError for duplicate graph projection")
