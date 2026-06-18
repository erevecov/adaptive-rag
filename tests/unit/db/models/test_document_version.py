"""Tests para el modelo DocumentVersion.

`document_versions` es el ancla de citas (decision D3 del design):
`normalized_text` es el texto fuente sobre el que se calculan los offsets
de chunks. Cada re-parseo crea una version nueva; las anteriores siguen
apuntando a sus chunks originales.
"""

from sqlalchemy import inspect, select

from adaptive_rag.db.base import Base
from adaptive_rag.db.models import Document, DocumentVersion, Project, Source
from adaptive_rag.db.session import create_engine_from_url, create_session_factory


def _make_session():
    engine = create_engine_from_url("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(
        engine,
        tables=[
            Project.__table__,
            Source.__table__,
            Document.__table__,
            DocumentVersion.__table__,
        ],
    )
    return create_session_factory(engine)()


def _make_document(session):
    project = Project(name="demo")
    session.add(project)
    session.commit()
    source = Source(
        project_id=project.id, source_type="web", external_id="id-1"
    )
    session.add(source)
    session.commit()
    document = Document(
        project_id=project.id, source_id=source.id, stable_id="doc-1"
    )
    session.add(document)
    session.commit()
    return document


def test_document_version_persists_normalized_text():
    session = _make_session()
    document = _make_document(session)

    text = "Texto normalizado de ejemplo."
    version = DocumentVersion(
        document_id=document.id,
        version_number=1,
        normalized_text=text,
        content_hash="sha256:abc",
        index_fingerprint="fp-1",
    )
    session.add(version)
    session.commit()
    session.expunge_all()

    fetched = session.execute(
        select(DocumentVersion).where(DocumentVersion.version_number == 1)
    ).scalar_one()

    assert fetched.normalized_text == text


def test_document_version_persists_parser_and_extraction_metadata():
    session = _make_session()
    document = _make_document(session)

    parser_meta = {"parser": "trafilatura", "version": "2.1"}
    extraction_meta = {"extracted_at": "2026-06-18T00:00:00Z"}
    version = DocumentVersion(
        document_id=document.id,
        version_number=1,
        normalized_text="x",
        content_hash="sha256:abc",
        index_fingerprint="fp-1",
        parser_metadata=parser_meta,
        extraction_metadata=extraction_meta,
    )
    session.add(version)
    session.commit()
    session.expunge_all()

    fetched = session.execute(
        select(DocumentVersion).where(DocumentVersion.document_id == document.id)
    ).scalar_one()

    assert fetched.parser_metadata == parser_meta
    assert fetched.extraction_metadata == extraction_meta


def test_document_version_required_fields_are_not_null():
    columns = {c.name: c for c in inspect(DocumentVersion).columns}

    for required in (
        "document_id",
        "version_number",
        "normalized_text",
        "content_hash",
        "index_fingerprint",
    ):
        assert columns[required].nullable is False, required


def test_document_version_has_foreign_key_to_documents():
    table = inspect(DocumentVersion).local_table
    fk_targets = {fk.column.table.name for fk in table.foreign_keys}

    assert "documents" in fk_targets


def test_re_indexing_creates_new_version_preserving_old():
    session = _make_session()
    document = _make_document(session)

    v1 = DocumentVersion(
        document_id=document.id,
        version_number=1,
        normalized_text="texto v1",
        content_hash="sha256:v1",
        index_fingerprint="fp-v1",
    )
    session.add(v1)
    session.commit()
    v2 = DocumentVersion(
        document_id=document.id,
        version_number=2,
        normalized_text="texto v2 reparseado",
        content_hash="sha256:v2",
        index_fingerprint="fp-v2",
    )
    session.add(v2)
    session.commit()
    session.expunge_all()

    versions = (
        session.execute(
            select(DocumentVersion)
            .where(DocumentVersion.document_id == document.id)
            .order_by(DocumentVersion.version_number)
        )
        .scalars()
        .all()
    )

    assert [v.version_number for v in versions] == [1, 2]
    assert versions[0].normalized_text == "texto v1"
    assert versions[1].normalized_text == "texto v2 reparseado"
