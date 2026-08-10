"""Tests para el modelo Workspace.

Estos tests definen el contrato del schema de proyectos antes de que el
modelo exista. Los defaults y constraints se validan funcionalmente sobre
SQLite in-memory; la columna de embedding (pgvector) se valida en
integracion.
"""

from sqlalchemy import inspect, select
from sqlalchemy.exc import IntegrityError

from adaptive_rag.db.base import Base
from adaptive_rag.db.models import Workspace
from adaptive_rag.db.session import create_engine_from_url, create_session_factory


def _make_session():
    engine = create_engine_from_url("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine, tables=[Workspace.__table__])
    return create_session_factory(engine)()


def test_workspace_embedding_mode_defaults_to_dense_sparse():
    session = _make_session()
    workspace = Workspace(name="demo")
    session.add(workspace)
    session.commit()

    assert workspace.embedding_mode == "dense_sparse"


def test_workspace_contextualization_enabled_defaults_to_true():
    session = _make_session()
    workspace = Workspace(name="demo")
    session.add(workspace)
    session.commit()

    assert workspace.retrieval_contextualization_enabled is True


def test_workspace_budget_config_persists_json():
    session = _make_session()
    config = {"max_tokens": 4096, "top_k": 8}
    workspace = Workspace(name="demo", budget_config_json=config)
    session.add(workspace)
    session.commit()
    session.expunge_all()

    fetched = session.execute(
        select(Workspace).where(Workspace.name == "demo")
    ).scalar_one()

    assert fetched.budget_config_json == config


def test_workspace_budget_config_column_matches_spec_name():
    columns = {c.name for c in inspect(Workspace).columns}

    assert "budget_config_json" in columns
    assert "budget_config" not in columns


def test_workspace_embedding_mode_check_rejects_invalid_value():
    session = _make_session()
    workspace = Workspace(name="demo", embedding_mode="invalid")

    try:
        session.add(workspace)
        session.commit()
    except IntegrityError:
        return
    finally:
        session.rollback()

    raise AssertionError("Expected IntegrityError for invalid embedding_mode")


def test_workspace_has_uuid_primary_key():
    columns = {c.name: c for c in inspect(Workspace).columns}

    assert "id" in columns
    assert columns["id"].primary_key


def test_workspace_name_column_is_required():
    columns = {c.name: c for c in inspect(Workspace).columns}

    assert columns["name"].nullable is False
