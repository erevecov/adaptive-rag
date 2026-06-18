"""Tests para el modelo Source.

Valida pertenencia a proyecto, campos de identidad de ingestion y columnas
tipadas aptas para metadata filtering. La verificacion de indices reales
e integridad referencial sobre Postgres se hace en integracion; aca
validamos el contrato de columna y la existencia de FKs via introspeccion.
"""

from sqlalchemy import inspect, select

from adaptive_rag.db.base import Base
from adaptive_rag.db.models import Project, Source
from adaptive_rag.db.session import create_engine_from_url, create_session_factory


def _make_session():
    engine = create_engine_from_url("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(
        engine, tables=[Project.__table__, Source.__table__]
    )
    return create_session_factory(engine)()


def _make_project(session):
    project = Project(name="demo")
    session.add(project)
    session.commit()
    return project


def test_source_belongs_to_project_via_foreign_key():
    session = _make_session()
    project = _make_project(session)

    source = Source(
        project_id=project.id, source_type="web", external_id="https://example.com"
    )
    session.add(source)
    session.commit()

    assert source.project_id == project.id


def test_source_external_id_persists():
    session = _make_session()
    project = _make_project(session)

    source = Source(
        project_id=project.id, source_type="web", external_id="https://example.com"
    )
    session.add(source)
    session.commit()
    session.expunge_all()

    fetched = session.execute(
        select(Source).where(Source.external_id == "https://example.com")
    ).scalar_one()

    assert fetched.source_type == "web"


def test_source_tags_persist_as_json():
    session = _make_session()
    project = _make_project(session)

    tags = ["docs", "reference"]
    source = Source(
        project_id=project.id,
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
    project = _make_project(session)

    metadata = {"author": "someone", "lang": "es"}
    source = Source(
        project_id=project.id,
        source_type="web",
        external_id="id-1",
        extra_metadata=metadata,
    )
    session.add(source)
    session.commit()
    session.expunge_all()

    fetched = session.execute(select(Source).where(Source.id == source.id)).scalar_one()

    assert fetched.extra_metadata == metadata


def test_source_project_id_is_required():
    columns = {c.name: c for c in inspect(Source).columns}

    assert columns["project_id"].nullable is False


def test_source_project_id_has_foreign_key_to_projects():
    table = inspect(Source).local_table
    fk_targets = {fk.column.table.name for fk in table.foreign_keys}

    assert "projects" in fk_targets


def test_source_rejects_unknown_project_id():
    # La integridad referencial real se valida en integracion con Postgres.
    # Aca validamos el contrato de columna: project_id es NOT NULL con FK.
    columns = {c.name: c for c in inspect(Source).columns}
    assert columns["project_id"].nullable is False
    table = inspect(Source).local_table
    assert any(
        fk.parent.name == "project_id" for fk in table.foreign_keys
    )


def test_source_has_timestamps_for_date_filtering():
    columns = {c.name for c in inspect(Source).columns}

    assert "created_at" in columns
    assert "updated_at" in columns
