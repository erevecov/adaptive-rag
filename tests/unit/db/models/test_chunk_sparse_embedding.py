"""Tests para el modelo ChunkSparseEmbedding.

Tabla aislada y opcional (decision D4): solo se puebla cuando un proyecto
usa `embedding_mode = dense_sparse`. Los proyectos dense-only operan sin
filas aca. Cada fila preserva metadata de reproducibilidad.
"""

from sqlalchemy import inspect, select

from adaptive_rag.db.base import Base
from adaptive_rag.db.models import (
    Chunk,
    ChunkSparseEmbedding,
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
            ChunkSparseEmbedding.__table__,
        ],
    )
    return create_session_factory(engine)()


def _make_chunk(session):
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
        normalized_text="abc",
        content_hash="sha256:abc",
        index_fingerprint="fp-1",
    )
    session.add(version)
    session.commit()
    chunk = Chunk(
        document_version_id=version.id, ordinal=0, char_start=0, char_end=3
    )
    session.add(chunk)
    session.commit()
    return chunk


def test_sparse_embedding_persists_indices_values_and_size():
    session = _make_session()
    chunk = _make_chunk(session)

    indices = [1, 42, 1000]
    values = [0.1, 0.5, 0.9]
    row = ChunkSparseEmbedding(
        chunk_id=chunk.id,
        sparse_indices=indices,
        sparse_values=values,
        sparse_size=3,
        input_hash="sha256:input",
        index_fingerprint="fp-sparse",
    )
    session.add(row)
    session.commit()
    session.expunge_all()

    fetched = session.execute(
        select(ChunkSparseEmbedding).where(ChunkSparseEmbedding.chunk_id == chunk.id)
    ).scalar_one()

    assert fetched.sparse_indices == indices
    assert fetched.sparse_values == values
    assert fetched.sparse_size == 3


def test_sparse_embedding_optional_tokens_persist():
    session = _make_session()
    chunk = _make_chunk(session)

    tokens = ["alpha", "beta"]
    row = ChunkSparseEmbedding(
        chunk_id=chunk.id,
        sparse_indices=[0, 1],
        sparse_values=[0.2, 0.8],
        sparse_size=2,
        sparse_tokens=tokens,
        input_hash="sha256:input",
        index_fingerprint="fp-sparse",
    )
    session.add(row)
    session.commit()
    session.expunge_all()

    fetched = session.execute(
        select(ChunkSparseEmbedding).where(ChunkSparseEmbedding.chunk_id == chunk.id)
    ).scalar_one()

    assert fetched.sparse_tokens == tokens


def test_sparse_embedding_reproducibility_fields_required():
    columns = {
        c.name: c for c in inspect(ChunkSparseEmbedding).columns
    }

    for required in (
        "chunk_id",
        "sparse_indices",
        "sparse_values",
        "sparse_size",
        "input_hash",
        "index_fingerprint",
    ):
        assert columns[required].nullable is False, required


def test_sparse_embedding_tokens_are_optional():
    columns = {
        c.name: c for c in inspect(ChunkSparseEmbedding).columns
    }

    assert columns["sparse_tokens"].nullable is True


def test_sparse_embedding_has_foreign_key_to_chunks():
    table = inspect(ChunkSparseEmbedding).local_table
    fk_targets = {fk.column.table.name for fk in table.foreign_keys}

    assert "chunks" in fk_targets
