"""Tests para el modelo Document.

Un document pertenece a un proyecto y a un source. Las queries de
repository deben poder filtrar por cualquiera de esos campos, por lo que
ambas columnas deben existir, ser NOT NULL y tener FK.
"""

from sqlalchemy import inspect, select
from sqlalchemy.exc import IntegrityError

from adaptive_rag.db.base import Base
from adaptive_rag.db.models import Document, Source, Workspace
from adaptive_rag.db.session import create_engine_from_url, create_session_factory


def _make_session():
    engine = create_engine_from_url("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(
        engine,
        tables=[Workspace.__table__, Source.__table__, Document.__table__],
    )
    return create_session_factory(engine)()


def _make_workspace_and_source(session):
    workspace = Workspace(name="demo")
    session.add(workspace)
    session.commit()
    source = Source(
        workspace_id=workspace.id, source_type="web", external_id="id-1"
    )
    session.add(source)
    session.commit()
    return workspace, source


def test_document_belongs_to_workspace_and_source():
    session = _make_session()
    workspace, source = _make_workspace_and_source(session)

    document = Document(
        workspace_id=workspace.id, source_id=source.id, stable_id="doc-1"
    )
    session.add(document)
    session.commit()

    assert document.workspace_id == workspace.id
    assert document.source_id == source.id


def test_document_stable_identifier_persists():
    session = _make_session()
    workspace, source = _make_workspace_and_source(session)

    document = Document(
        workspace_id=workspace.id, source_id=source.id, stable_id="doc-abc"
    )
    session.add(document)
    session.commit()
    session.expunge_all()

    fetched = session.execute(
        select(Document).where(Document.stable_id == "doc-abc")
    ).scalar_one()

    assert fetched.workspace_id == workspace.id


def test_document_stable_id_is_unique_within_source():
    session = _make_session()
    workspace, source = _make_workspace_and_source(session)
    document = Document(
        workspace_id=workspace.id, source_id=source.id, stable_id="doc-abc"
    )
    duplicate = Document(
        workspace_id=workspace.id, source_id=source.id, stable_id="doc-abc"
    )

    session.add(document)
    session.commit()
    session.add(duplicate)

    try:
        session.commit()
    except IntegrityError:
        return
    finally:
        session.rollback()

    raise AssertionError("Expected IntegrityError for duplicate document identity")


def test_document_workspace_id_and_source_id_are_required():
    columns = {c.name: c for c in inspect(Document).columns}

    assert columns["workspace_id"].nullable is False
    assert columns["source_id"].nullable is False


def test_document_has_foreign_keys_to_workspaces_and_sources():
    table = inspect(Document).local_table
    fk_targets = {fk.column.table.name for fk in table.foreign_keys}

    assert "workspaces" in fk_targets
    assert "sources" in fk_targets


def test_document_workspace_and_source_are_indexed():
    # SQLAlchemy expone index=True como columnas en table.indexes o via
    # el flag de columna. Validamos que existan indices que cubran esas
    # columnas (se creen como indices individuales o compuestos).
    table = inspect(Document).local_table
    indexed_columns: set[str] = set()
    for index in table.indexes:
        indexed_columns.update(col.name for col in index.columns)

    assert "workspace_id" in indexed_columns
    assert "source_id" in indexed_columns
