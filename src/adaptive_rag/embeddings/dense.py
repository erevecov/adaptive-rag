"""Baseline de embeddings densos con providers deterministas."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Protocol
from uuid import UUID

from sqlalchemy.orm import Session

from adaptive_rag.db.models import EMBEDDING_DIMENSIONS, Chunk, DocumentVersion
from adaptive_rag.db.repositories import ChunkRepository, DocumentRepository

DENSE_EMBEDDING_METADATA_VERSION = "dense_embedding_v1"


class DenseEmbeddingPipelineError(ValueError):
    """Error no retryable del baseline de embeddings densos."""


class DenseEmbeddingProvider(Protocol):
    provider_name: str
    model_name: str
    dimensions: int

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Genera embeddings densos para una lista de inputs."""


@dataclass(frozen=True, slots=True)
class DenseEmbeddingInput:
    chunk: Chunk
    chunk_text: str
    embedding_input_text: str
    lexical_input_text: str
    embedding_input_hash: str
    lexical_input_hash: str
    input_kind: str


@dataclass(frozen=True, slots=True)
class DenseEmbeddingRunResult:
    document_version: DocumentVersion
    chunks: list[Chunk]
    embedded_chunk_count: int
    reused_chunk_count: int


class FakeDenseEmbeddingProvider:
    """Provider fake determinista para tests y smoke local."""

    provider_name = "fake"
    model_name = "fake-embedding-v1"
    dimensions = EMBEDDING_DIMENSIONS

    def __init__(self) -> None:
        self.inputs: list[str] = []

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        self.inputs.extend(texts)
        return [_deterministic_vector(text, self.dimensions) for text in texts]


class EmbeddingInputBuilder:
    """Construye inputs de embedding y lexical desde chunks originales."""

    def build(
        self,
        *,
        chunk: Chunk,
        document_version: DocumentVersion,
    ) -> DenseEmbeddingInput:
        text = document_version.normalized_text
        if chunk.char_start < 0 or chunk.char_end > len(text):
            raise DenseEmbeddingPipelineError("chunk offsets are outside document text")
        if chunk.char_end <= chunk.char_start:
            raise DenseEmbeddingPipelineError("chunk offsets are empty")

        chunk_text = text[chunk.char_start : chunk.char_end]
        contextual_summary = (
            chunk.contextual_summary.strip()
            if isinstance(chunk.contextual_summary, str)
            else ""
        )
        if contextual_summary:
            input_kind = "contextual_summary_plus_chunk_text"
            embedding_input_text = f"{contextual_summary}\n\n{chunk_text}"
        else:
            input_kind = "chunk_text"
            embedding_input_text = chunk_text

        lexical_input_text = embedding_input_text
        return DenseEmbeddingInput(
            chunk=chunk,
            chunk_text=chunk_text,
            embedding_input_text=embedding_input_text,
            lexical_input_text=lexical_input_text,
            embedding_input_hash=_sha256_text(embedding_input_text),
            lexical_input_hash=_sha256_text(lexical_input_text),
            input_kind=input_kind,
        )


class DenseEmbeddingPipeline:
    """Persiste embeddings densos sobre chunks ya creados."""

    def __init__(
        self,
        session: Session,
        *,
        provider: DenseEmbeddingProvider,
        input_builder: EmbeddingInputBuilder | None = None,
    ) -> None:
        self._chunk_repo = ChunkRepository(session)
        self._document_repo = DocumentRepository(session)
        self._provider = provider
        self._input_builder = input_builder or EmbeddingInputBuilder()

    def embed_document_version(
        self,
        *,
        project_id: UUID,
        document_version_id: UUID,
    ) -> DenseEmbeddingRunResult:
        document_version = self._document_repo.get_version(
            project_id=project_id,
            document_version_id=document_version_id,
        )
        if document_version is None:
            raise DenseEmbeddingPipelineError(
                "document version does not belong to project"
            )

        chunks = self._chunk_repo.list_by_document_version(
            project_id=project_id,
            document_version_id=document_version_id,
        )
        if not chunks:
            raise DenseEmbeddingPipelineError("document version has no chunks")

        inputs = [
            self._input_builder.build(chunk=chunk, document_version=document_version)
            for chunk in chunks
        ]
        pending_inputs = [
            embedding_input
            for embedding_input in inputs
            if not self._has_current_embedding(embedding_input)
        ]
        if not pending_inputs:
            return DenseEmbeddingRunResult(
                document_version=document_version,
                chunks=chunks,
                embedded_chunk_count=0,
                reused_chunk_count=len(chunks),
            )

        self._validate_provider_dimensions()
        embeddings = self._provider.embed_texts(
            [embedding_input.embedding_input_text for embedding_input in pending_inputs]
        )
        self._validate_embeddings(embeddings, expected_count=len(pending_inputs))

        for embedding_input, embedding in zip(pending_inputs, embeddings, strict=True):
            self._chunk_repo.update_dense_embedding(
                project_id=project_id,
                chunk_id=embedding_input.chunk.id,
                embedding=embedding,
                embedding_metadata=self._embedding_metadata(embedding_input),
            )

        return DenseEmbeddingRunResult(
            document_version=document_version,
            chunks=chunks,
            embedded_chunk_count=len(pending_inputs),
            reused_chunk_count=len(chunks) - len(pending_inputs),
        )

    def _has_current_embedding(self, embedding_input: DenseEmbeddingInput) -> bool:
        chunk = embedding_input.chunk
        metadata = chunk.embedding_metadata or {}
        return (
            chunk.embedding is not None
            and len(chunk.embedding) == self._provider.dimensions
            and metadata.get("embedding_metadata_version")
            == DENSE_EMBEDDING_METADATA_VERSION
            and metadata.get("embedding_provider") == self._provider.provider_name
            and metadata.get("embedding_model") == self._provider.model_name
            and metadata.get("embedding_dimensions") == self._provider.dimensions
            and metadata.get("embedding_input_hash")
            == embedding_input.embedding_input_hash
            and metadata.get("lexical_input_hash") == embedding_input.lexical_input_hash
        )

    def _validate_embeddings(
        self,
        embeddings: list[list[float]],
        *,
        expected_count: int,
    ) -> None:
        if len(embeddings) != expected_count:
            raise DenseEmbeddingPipelineError("embedding provider returned wrong count")
        self._validate_provider_dimensions()
        for embedding in embeddings:
            if len(embedding) != EMBEDDING_DIMENSIONS:
                raise DenseEmbeddingPipelineError(
                    "embedding dimension mismatch: "
                    f"expected {EMBEDDING_DIMENSIONS}, got {len(embedding)}"
                )

    def _validate_provider_dimensions(self) -> None:
        if self._provider.dimensions != EMBEDDING_DIMENSIONS:
            raise DenseEmbeddingPipelineError(
                "embedding dimension mismatch: "
                f"expected {EMBEDDING_DIMENSIONS}, got {self._provider.dimensions}"
            )

    def _embedding_metadata(
        self,
        embedding_input: DenseEmbeddingInput,
    ) -> dict[str, Any]:
        return {
            "embedding_dimensions": self._provider.dimensions,
            "embedding_input_hash": embedding_input.embedding_input_hash,
            "embedding_input_kind": embedding_input.input_kind,
            "embedding_index_fingerprint": _embedding_fingerprint(
                provider_name=self._provider.provider_name,
                model_name=self._provider.model_name,
                dimensions=self._provider.dimensions,
                input_hash=embedding_input.embedding_input_hash,
            ),
            "embedding_metadata_version": DENSE_EMBEDDING_METADATA_VERSION,
            "embedding_model": self._provider.model_name,
            "embedding_provider": self._provider.provider_name,
            "lexical_input_hash": embedding_input.lexical_input_hash,
        }


def _deterministic_vector(text: str, dimensions: int) -> list[float]:
    digest = hashlib.sha256(text.encode("utf-8")).digest()
    values: list[float] = []
    for index in range(dimensions):
        byte = digest[index % len(digest)]
        values.append((byte + index % 17) / 272.0)
    return values


def _embedding_fingerprint(
    *,
    provider_name: str,
    model_name: str,
    dimensions: int,
    input_hash: str,
) -> str:
    payload = {
        "dimensions": dimensions,
        "input_hash": input_hash,
        "metadata_version": DENSE_EMBEDDING_METADATA_VERSION,
        "model": model_name,
        "provider": provider_name,
    }
    return _sha256_text(json.dumps(payload, sort_keys=True, separators=(",", ":")))


def _sha256_text(value: str) -> str:
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()
    return f"sha256:{digest}"
