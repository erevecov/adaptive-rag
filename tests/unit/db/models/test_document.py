"""Tests para el modelo Document.

Un document pertenece a un proyecto y a un source. Las queries de
repository deben poder filtrar por cualquiera de esos campos, por lo que
ambas columnas deben existir, ser NOT NULL y tener FK.
"""

from sqlalchemy import inspect, select

from adaptive_rag.db.base import Base
from adaptive_rag.db.models import Document, Project, Source
from adaptive_rag.db.session import create_engine_from_url, create_session_factory


def _make_session():
    engine = create_engine_from_url("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(
        engine,
        tables=[Project.__table__, Source.__table__, Document.__table__],
    )
    return create_session_factory(engine)()


def _make_project_and_source(session):
    project = Project(name="demo")
    session.add(project)
    session.commit()
    source = Source(
        project_id=project.id, source_type="web", external_id="id-1"
    )
    session.add(source)
    session.commit()
    return project, source


def test_document_belongs_to_project_and_source():
    session = _make_session()
    project, source = _make_project_and_source(session)

    document = Document(
        project_id=project.id, source_id=source.id, stable_id="doc-1"
    )
    session.add(document)
    session.commit()

    assert document.project_id == project.id
    assert document.source_id == source.id


def test_document_stable_identifier_persists():
    session = _make_session()
    project, source = _make_project_and_source(session)

    document = Document(
        project_id=project.id, source_id=source.id, stable_id="doc-abc"
    )
    session.add(document)
    session.commit()
    session.expunge_all()

    fetched = session.execute(
        select(Document).where(Document.stable_id == "doc-abc")
    ).scalar_one()

    assert fetched.project_id == project.id


def test_document_project_id_and_source_id_are_required():
    columns = {c.name: c for c in inspect(Document).columns}

    assert columns["project_id"].nullable is False
    assert columns["source_id"].nullable is False


def test_document_has_foreign_keys_to_projects_and_sources():
    table = inspect(Document).local_table
    fk_targets = {fk.column.table.name for fk in table.foreign_keys}

    assert "projects" in fk_targets
    assert "sources" in fk_targets


def test_document_project_and_source_are_indexed():
    # SQLAlchemy expone index=True como columnas en table.indexes o via
    # el flag de columna. Validamos que existan indices que cubran esas
    # columnas (se creen como indices individuales o compuestos).
    table = inspect(Document).local_table
    indexed_columns: set[str] = set()
    for index in table.indexes:
        indexed_columns.update(col.name for col in index.columns)

    assert "project_id" in indexed_columns
    assert "source_id" in indexed_columns
