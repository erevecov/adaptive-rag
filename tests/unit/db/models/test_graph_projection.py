"""Tests para el estado Postgres de proyeccion graph por proyecto."""

from __future__ import annotations

from sqlalchemy.exc import IntegrityError

from adaptive_rag.db.base import Base
from adaptive_rag.db.models import GraphProjection, Project
from adaptive_rag.db.session import create_engine_from_url, create_session_factory


def _make_session():
    engine = create_engine_from_url("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(
        engine,
        tables=[Project.__table__, GraphProjection.__table__],
    )
    return create_session_factory(engine)()


def test_graph_projection_defaults_to_disabled_neo4j_projection() -> None:
    session = _make_session()
    project = Project(name="demo")
    session.add(project)
    session.flush()
    projection = GraphProjection(project_id=project.id)
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
    project = Project(name="demo")
    session.add(project)
    session.flush()
    projection = GraphProjection(project_id=project.id, status="invalid")

    try:
        session.add(projection)
        session.commit()
    except IntegrityError:
        return
    finally:
        session.rollback()

    raise AssertionError("Expected IntegrityError for invalid graph projection status")


def test_graph_projection_is_unique_per_project_and_backend() -> None:
    session = _make_session()
    project = Project(name="demo")
    session.add(project)
    session.flush()
    session.add(GraphProjection(project_id=project.id, backend="neo4j"))
    session.add(GraphProjection(project_id=project.id, backend="neo4j"))

    try:
        session.commit()
    except IntegrityError:
        return
    finally:
        session.rollback()

    raise AssertionError("Expected IntegrityError for duplicate graph projection")
