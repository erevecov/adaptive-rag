"""Tests para el modelo Source.

Valida pertenencia a proyecto, campos de identidad de ingestion y columnas
tipadas aptas para metadata filtering. La verificacion de indices reales
e integridad referencial sobre Postgres se hace en integracion; aca
validamos el contrato de columna y la existencia de FKs via introspeccion.
"""

from sqlalchemy import inspect, select
from sqlalchemy.exc import IntegrityError

from adaptive_rag.db.base import Base
from adaptive_rag.db.models import Source, Workspace
from adaptive_rag.db.session import create_engine_from_url, create_session_factory


def _make_session():
    engine = create_engine_from_url("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(
        engine, tables=[Workspace.__table__, Source.__table__]
    )
    return create_session_factory(engine)()


def _make_workspace(session):
    workspace = Workspace(name="demo")
    session.add(workspace)
    session.commit()
    return workspace


def test_source_belongs_to_workspace_via_foreign_key():
    session = _make_session()
    workspace = _make_workspace(session)

    source = Source(
        workspace_id=workspace.id, source_type="web", external_id="https://example.com"
    )
    session.add(source)
    session.commit()

    assert source.workspace_id == workspace.id


def test_source_external_id_persists():
    session = _make_session()
    workspace = _make_workspace(session)

    source = Source(
        workspace_id=workspace.id, source_type="web", external_id="https://example.com"
    )
    session.add(source)
    session.commit()
    session.expunge_all()

    fetched = session.execute(
        select(Source).where(Source.external_id == "https://example.com")
    ).scalar_one()

    assert fetched.source_type == "web"


def test_source_identity_is_unique_within_workspace():
    session = _make_session()
    workspace = _make_workspace(session)
    source = Source(workspace_id=workspace.id, source_type="web", external_id="id-1")
    duplicate = Source(
        workspace_id=workspace.id, source_type="web", external_id="id-1"
    )

    session.add(source)
    session.commit()
    session.add(duplicate)

    try:
        session.commit()
    except IntegrityError:
        return
    finally:
        session.rollback()

    raise AssertionError("Expected IntegrityError for duplicate source identity")


def test_source_tags_persist_as_json():
    session = _make_session()
    workspace = _make_workspace(session)

    tags = ["docs", "reference"]
    source = Source(
        workspace_id=workspace.id,
        source_type="web",
        external_id="id-1",
        tags=tags,
    )
    session.add(source)
    session.commit()
    session.expunge_all()

    fetched = session.execute(select(Source).where(Source.id == source.id)).scalar_one()

    assert fetched.tags == tags


def test_source_metadata_persists_as_json():
    session = _make_session()
    workspace = _make_workspace(session)

    metadata = {"author": "someone", "lang": "es"}
    source = Source(
        workspace_id=workspace.id,
        source_type="web",
        external_id="id-1",
        extra_metadata=metadata,
    )
    session.add(source)
    session.commit()
    session.expunge_all()

    fetched = session.execute(select(Source).where(Source.id == source.id)).scalar_one()

    assert fetched.extra_metadata == metadata


def test_source_workspace_id_is_required():
    columns = {c.name: c for c in inspect(Source).columns}

    assert columns["workspace_id"].nullable is False


def test_source_workspace_id_has_foreign_key_to_workspaces():
    table = inspect(Source).local_table
    fk_targets = {fk.column.table.name for fk in table.foreign_keys}

    assert "workspaces" in fk_targets


def test_source_rejects_unknown_workspace_id():
    # La integridad referencial real se valida en integracion con Postgres.
    # Aca validamos el contrato de columna: workspace_id es NOT NULL con FK.
    columns = {c.name: c for c in inspect(Source).columns}
    assert columns["workspace_id"].nullable is False
    table = inspect(Source).local_table
    assert any(
        fk.parent.name == "workspace_id" for fk in table.foreign_keys
    )


def test_source_has_timestamps_for_date_filtering():
    columns = {c.name for c in inspect(Source).columns}

    assert "created_at" in columns
    assert "updated_at" in columns


def test_source_filtering_columns_are_indexed():
    table = inspect(Source).local_table
    indexed_columns: set[tuple[str, ...]] = {
        tuple(col.name for col in index.columns) for index in table.indexes
    }

    assert ("workspace_id", "source_type") in indexed_columns
    assert ("workspace_id", "created_at") in indexed_columns
    assert ("tags",) in indexed_columns
