"""Tests para el modelo Project.

Estos tests definen el contrato del schema de proyectos antes de que el
modelo exista. Los defaults y constraints se validan funcionalmente sobre
SQLite in-memory; la columna de embedding (pgvector) se valida en
integracion.
"""

from sqlalchemy import inspect, select
from sqlalchemy.exc import IntegrityError

from adaptive_rag.db.base import Base
from adaptive_rag.db.models import Project
from adaptive_rag.db.session import create_engine_from_url, create_session_factory


def _make_session():
    engine = create_engine_from_url("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine, tables=[Project.__table__])
    return create_session_factory(engine)()


def test_project_embedding_mode_defaults_to_dense():
    session = _make_session()
    project = Project(name="demo")
    session.add(project)
    session.commit()

    assert project.embedding_mode == "dense"


def test_project_contextualization_enabled_defaults_to_true():
    session = _make_session()
    project = Project(name="demo")
    session.add(project)
    session.commit()

    assert project.retrieval_contextualization_enabled is True


def test_project_budget_config_persists_json():
    session = _make_session()
    config = {"max_tokens": 4096, "top_k": 8}
    project = Project(name="demo", budget_config_json=config)
    session.add(project)
    session.commit()
    session.expunge_all()

    fetched = session.execute(
        select(Project).where(Project.name == "demo")
    ).scalar_one()

    assert fetched.budget_config_json == config


def test_project_budget_config_column_matches_spec_name():
    columns = {c.name for c in inspect(Project).columns}

    assert "budget_config_json" in columns
    assert "budget_config" not in columns


def test_project_embedding_mode_check_rejects_invalid_value():
    session = _make_session()
    project = Project(name="demo", embedding_mode="invalid")

    try:
        session.add(project)
        session.commit()
    except IntegrityError:
        return
    finally:
        session.rollback()

    raise AssertionError("Expected IntegrityError for invalid embedding_mode")


def test_project_has_uuid_primary_key():
    columns = {c.name: c for c in inspect(Project).columns}

    assert "id" in columns
    assert columns["id"].primary_key


def test_project_name_column_is_required():
    columns = {c.name: c for c in inspect(Project).columns}

    assert columns["name"].nullable is False
