"""Sparse embeddings opt-in para retrieval dense_sparse."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from dataclasses import dataclass
from typing import Any, Protocol
from uuid import UUID

from sqlalchemy.orm import Session

from adaptive_rag.db.models import EMBEDDING_DIMENSIONS, Chunk, DocumentVersion
from adaptive_rag.db.repositories import (
    ChunkRepository,
    DocumentRepository,
    SparseEmbeddingRepository,
)
from adaptive_rag.embeddings.dense import DenseEmbeddingInput, EmbeddingInputBuilder

SPARSE_EMBEDDING_METADATA_VERSION = "sparse_embedding_v1"


class SparseEmbeddingProvider(Protocol):
    provider_name: str
    model_name: str
    dimensions: int

    def embed_documents(self, texts: list[str]) -> list[SparseEmbeddingVector]:
        """Genera sparse embeddings para documentos/chunks."""

    def embed_query(self, text: str) -> SparseEmbeddingVector:
        """Genera sparse embedding para una query."""


class SparseEmbeddingPipelineError(ValueError):
    """Error no retryable del backfill de sparse embeddings."""


@dataclass(frozen=True, slots=True)
class SparseEmbeddingVector:
    indices: tuple[int, ...]
    values: tuple[float, ...]
    tokens: tuple[str, ...] | None = None

    def __post_init__(self) -> None:
        if len(self.indices) != len(self.values):
            raise ValueError("sparse indices and values must have the same length")
        if self.tokens is not None and len(self.tokens) != len(self.indices):
            raise ValueError("sparse tokens must match sparse indices length")

    @property
    def sparse_size(self) -> int:
        return len(self.indices)

    def as_dict(self) -> dict[int, float]:
        values: dict[int, float] = {}
        for index, value in zip(self.indices, self.values, strict=True):
            values[index] = values.get(index, 0.0) + value
        return values


class FakeSparseEmbeddingProvider:
    """Provider sparse determinista para tests, evals offline y smoke local."""

    provider_name = "fake"
    model_name = "fake-sparse-embedding-v1"
    dimensions = EMBEDDING_DIMENSIONS

    def __init__(self) -> None:
        self.document_inputs: list[str] = []
        self.query_inputs: list[str] = []

    def embed_documents(self, texts: list[str]) -> list[SparseEmbeddingVector]:
        self.document_inputs.extend(texts)
        return [_deterministic_sparse_vector(text, self.dimensions) for text in texts]

    def embed_query(self, text: str) -> SparseEmbeddingVector:
        self.query_inputs.append(text)
        return _deterministic_sparse_vector(text, self.dimensions)


@dataclass(frozen=True, slots=True)
class SparseEmbeddingRunResult:
    document_version: DocumentVersion
    chunks: list[Chunk]
    embedded_chunk_count: int
    reused_chunk_count: int


class SparseEmbeddingPipeline:
    """Persiste sparse embeddings sobre chunks ya creados."""

    def __init__(
        self,
        session: Session,
        *,
        provider: SparseEmbeddingProvider,
        input_builder: EmbeddingInputBuilder | None = None,
    ) -> None:
        self._chunk_repo = ChunkRepository(session)
        self._document_repo = DocumentRepository(session)
        self._sparse_repo = SparseEmbeddingRepository(session)
        self._provider = provider
        self._input_builder = input_builder or EmbeddingInputBuilder()

    def embed_document_version(
        self,
        *,
        project_id: UUID,
        document_version_id: UUID,
    ) -> SparseEmbeddingRunResult:
        document_version = self._document_repo.get_version(
            project_id=project_id,
            document_version_id=document_version_id,
        )
        if document_version is None:
            raise SparseEmbeddingPipelineError(
                "document version does not belong to project"
            )

        chunks = self._chunk_repo.list_by_document_version(
            project_id=project_id,
            document_version_id=document_version_id,
        )
        if not chunks:
            raise SparseEmbeddingPipelineError("document version has no chunks")

        inputs = [
            self._input_builder.build(chunk=chunk, document_version=document_version)
            for chunk in chunks
        ]
        pending_inputs = [
            embedding_input
            for embedding_input in inputs
            if not self._has_current_sparse_embedding(
                project_id=project_id,
                embedding_input=embedding_input,
            )
        ]
        if not pending_inputs:
            return SparseEmbeddingRunResult(
                document_version=document_version,
                chunks=chunks,
                embedded_chunk_count=0,
                reused_chunk_count=len(chunks),
            )

        self._validate_provider_dimensions()
        vectors = self._provider.embed_documents(
            [
                embedding_input.embedding_input_text
                for embedding_input in pending_inputs
            ]
        )
        if len(vectors) != len(pending_inputs):
            raise SparseEmbeddingPipelineError(
                "sparse embedding provider returned wrong count"
            )

        for embedding_input, vector in zip(pending_inputs, vectors, strict=True):
            self._sparse_repo.upsert_current(
                project_id=project_id,
                chunk_id=embedding_input.chunk.id,
                vector=vector,
                input_hash=embedding_input.embedding_input_hash,
                index_fingerprint=self._index_fingerprint(embedding_input),
                extra_metadata=self._sparse_metadata(embedding_input),
            )

        return SparseEmbeddingRunResult(
            document_version=document_version,
            chunks=chunks,
            embedded_chunk_count=len(pending_inputs),
            reused_chunk_count=len(chunks) - len(pending_inputs),
        )

    def _has_current_sparse_embedding(
        self,
        *,
        project_id: UUID,
        embedding_input: DenseEmbeddingInput,
    ) -> bool:
        row = self._sparse_repo.get_current(
            project_id=project_id,
            chunk_id=embedding_input.chunk.id,
            index_fingerprint=self._index_fingerprint(embedding_input),
        )
        if row is None:
            return False
        metadata = row.extra_metadata or {}
        return (
            row.input_hash == embedding_input.embedding_input_hash
            and row.sparse_size == len(row.sparse_indices)
            and len(row.sparse_indices) == len(row.sparse_values)
            and metadata.get("sparse_metadata_version")
            == SPARSE_EMBEDDING_METADATA_VERSION
            and metadata.get("sparse_provider") == self._provider.provider_name
            and metadata.get("sparse_model") == self._provider.model_name
            and metadata.get("sparse_dimensions") == self._provider.dimensions
            and metadata.get("sparse_input_hash")
            == embedding_input.embedding_input_hash
        )

    def _validate_provider_dimensions(self) -> None:
        if self._provider.dimensions != EMBEDDING_DIMENSIONS:
            raise SparseEmbeddingPipelineError(
                "sparse embedding dimension mismatch: "
                f"expected {EMBEDDING_DIMENSIONS}, got {self._provider.dimensions}"
            )

    def _index_fingerprint(self, embedding_input: DenseEmbeddingInput) -> str:
        return _sparse_fingerprint(
            provider_name=self._provider.provider_name,
            model_name=self._provider.model_name,
            dimensions=self._provider.dimensions,
            input_hash=embedding_input.embedding_input_hash,
            text_type="document",
        )

    def _sparse_metadata(
        self,
        embedding_input: DenseEmbeddingInput,
    ) -> dict[str, Any]:
        index_fingerprint = self._index_fingerprint(embedding_input)
        return {
            "lexical_input_hash": embedding_input.lexical_input_hash,
            "sparse_dimensions": self._provider.dimensions,
            "sparse_index_fingerprint": index_fingerprint,
            "sparse_input_hash": embedding_input.embedding_input_hash,
            "sparse_input_kind": embedding_input.input_kind,
            "sparse_metadata_version": SPARSE_EMBEDDING_METADATA_VERSION,
            "sparse_model": self._provider.model_name,
            "sparse_provider": self._provider.provider_name,
            "sparse_text_type": "document",
        }


def sparse_dot_product(
    left: SparseEmbeddingVector,
    right: SparseEmbeddingVector,
) -> float:
    left_values = left.as_dict()
    score = 0.0
    for index, value in zip(right.indices, right.values, strict=True):
        score += left_values.get(index, 0.0) * value
    return score


def _deterministic_sparse_vector(text: str, dimensions: int) -> SparseEmbeddingVector:
    counts = Counter(_tokens(text))
    if not counts:
        return SparseEmbeddingVector(indices=(), values=(), tokens=())

    weighted: dict[int, tuple[float, str]] = {}
    for token, count in counts.items():
        index = _token_index(token, dimensions)
        value = float(count)
        existing = weighted.get(index)
        if existing is None:
            weighted[index] = (value, token)
        else:
            weighted[index] = (existing[0] + value, existing[1])

    ordered = sorted(weighted.items(), key=lambda item: item[0])
    return SparseEmbeddingVector(
        indices=tuple(index for index, _item in ordered),
        values=tuple(value for _index, (value, _token) in ordered),
        tokens=tuple(token for _index, (_value, token) in ordered),
    )


def _tokens(text: str) -> tuple[str, ...]:
    return tuple(part.lower() for part in text.split() if part.strip())


def _token_index(token: str, dimensions: int) -> int:
    digest = hashlib.sha256(token.encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big") % dimensions


def _sparse_fingerprint(
    *,
    provider_name: str,
    model_name: str,
    dimensions: int,
    input_hash: str,
    text_type: str,
) -> str:
    payload = {
        "dimensions": dimensions,
        "input_hash": input_hash,
        "metadata_version": SPARSE_EMBEDDING_METADATA_VERSION,
        "model": model_name,
        "provider": provider_name,
        "text_type": text_type,
    }
    return _sha256_text(json.dumps(payload, sort_keys=True, separators=(",", ":")))


def _sha256_text(value: str) -> str:
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()
    return f"sha256:{digest}"
