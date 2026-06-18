"""Tests para el modelo Chunk.

Valida offsets de cita (`char_start`, `char_end`), linaje (`ordinal`,
`prev_chunk_id`, `next_chunk_id`), metadata de seccion/chunker y el campo
de embedding denso. La columna `vector(1024)` no se puede crear en SQLite,
por lo que el tipo se declara portable y su dimension exacta se valida en
integracion contra pgvector.
"""

from sqlalchemy import inspect, select
from sqlalchemy.exc import IntegrityError

from adaptive_rag.db.base import Base
from adaptive_rag.db.models import (
    Chunk,
    Document,
    DocumentVersion,
    Project,
    Source,
)
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
            Chunk.__table__,
        ],
    )
    return create_session_factory(engine)()


def _make_version(session):
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
    version = DocumentVersion(
        document_id=document.id,
        version_number=1,
        normalized_text="abcdefghij",
        content_hash="sha256:abc",
        index_fingerprint="fp-1",
    )
    session.add(version)
    session.commit()
    return version


def test_chunk_offsets_persist():
    session = _make_session()
    version = _make_version(session)

    chunk = Chunk(
        document_version_id=version.id,
        ordinal=0,
        char_start=0,
        char_end=5,
        token_count=5,
    )
    session.add(chunk)
    session.commit()
    session.expunge_all()

    fetched = session.execute(select(Chunk).where(Chunk.ordinal == 0)).scalar_one()

    assert fetched.char_start == 0
    assert fetched.char_end == 5


def test_chunk_lineage_persists():
    session = _make_session()
    version = _make_version(session)

    c0 = Chunk(
        document_version_id=version.id, ordinal=0, char_start=0, char_end=5
    )
    c1 = Chunk(
        document_version_id=version.id, ordinal=1, char_start=5, char_end=10
    )
    session.add_all([c0, c1])
    session.commit()

    c0.next_chunk_id = c1.id
    c1.prev_chunk_id = c0.id
    session.commit()
    session.expunge_all()

    fetched = (
        session.execute(
            select(Chunk)
            .where(Chunk.document_version_id == version.id)
            .order_by(Chunk.ordinal)
        )
        .scalars()
        .all()
    )

    assert fetched[0].next_chunk_id == fetched[1].id
    assert fetched[1].prev_chunk_id == fetched[0].id


def test_chunk_section_and_chunker_metadata_persist():
    session = _make_session()
    version = _make_version(session)

    section = {"heading": "Intro"}
    chunker = {"strategy": "fixed", "size": 512}
    chunk = Chunk(
        document_version_id=version.id,
        ordinal=0,
        char_start=0,
        char_end=5,
        section_metadata=section,
        chunker_metadata=chunker,
    )
    session.add(chunk)
    session.commit()
    session.expunge_all()

    fetched = session.execute(select(Chunk).where(Chunk.ordinal == 0)).scalar_one()

    assert fetched.section_metadata == section
    assert fetched.chunker_metadata == chunker


def test_chunk_reserved_contextual_fields_exist():
    columns = {c.name for c in inspect(Chunk).columns}

    # Campos reservados para contextual retrieval (no implementado en v1).
    assert "contextual_summary" in columns


def test_chunk_embedding_column_exists():
    columns = {c.name for c in inspect(Chunk).columns}

    # La columna de embedding denso debe existir; su tipo y dimension
    # exactos (vector(1024)) se validan en integracion contra pgvector.
    assert "embedding" in columns


def test_chunk_required_fields_are_not_null():
    columns = {c.name: c for c in inspect(Chunk).columns}

    for required in ("document_version_id", "ordinal", "char_start", "char_end"):
        assert columns[required].nullable is False, required


def test_chunk_has_foreign_key_to_document_versions():
    table = inspect(Chunk).local_table
    fk_targets = {fk.column.table.name for fk in table.foreign_keys}

    assert "document_versions" in fk_targets


def test_chunk_ordinal_is_unique_per_document_version():
    session = _make_session()
    version = _make_version(session)
    c0 = Chunk(
        document_version_id=version.id, ordinal=0, char_start=0, char_end=5
    )
    duplicate = Chunk(
        document_version_id=version.id, ordinal=0, char_start=5, char_end=10
    )

    session.add(c0)
    session.commit()
    session.add(duplicate)

    try:
        session.commit()
    except IntegrityError:
        return
    finally:
        session.rollback()

    raise AssertionError("Expected IntegrityError for duplicate chunk ordinal")


def test_chunk_offsets_must_be_non_empty_forward_ranges():
    session = _make_session()
    version = _make_version(session)
    chunk = Chunk(
        document_version_id=version.id, ordinal=0, char_start=5, char_end=5
    )

    session.add(chunk)

    try:
        session.commit()
    except IntegrityError:
        return
    finally:
        session.rollback()

    raise AssertionError("Expected IntegrityError for empty chunk range")


def test_chunk_token_count_cannot_be_negative():
    session = _make_session()
    version = _make_version(session)
    chunk = Chunk(
        document_version_id=version.id,
        ordinal=0,
        char_start=0,
        char_end=5,
        token_count=-1,
    )

    session.add(chunk)

    try:
        session.commit()
    except IntegrityError:
        return
    finally:
        session.rollback()

    raise AssertionError("Expected IntegrityError for negative token count")
