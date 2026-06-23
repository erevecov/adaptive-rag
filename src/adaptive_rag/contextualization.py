"""Generated contextual summaries for chunk indexing."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Protocol
from uuid import UUID

from sqlalchemy.orm import Session

from adaptive_rag.db.models import Chunk, DocumentVersion
from adaptive_rag.db.repositories import ChunkRepository, DocumentRepository


class ContextualizationPipelineError(ValueError):
    """Error no retryable del pipeline de contextualizacion."""


@dataclass(frozen=True, slots=True)
class ContextualizationRequest:
    project_id: UUID
    document_version_id: UUID
    chunk_id: UUID
    ordinal: int
    document_text: str
    chunk_text: str
    section_metadata: Mapping[str, Any] | None


@dataclass(frozen=True, slots=True)
class GeneratedContextualSummary:
    chunk_id: UUID
    summary: str
    metadata: Mapping[str, Any]


class Contextualizer(Protocol):
    provider_name: str
    model_name: str

    def contextualize(
        self,
        request: ContextualizationRequest,
    ) -> GeneratedContextualSummary:
        """Generate a bounded contextual summary for one chunk."""


@dataclass(frozen=True, slots=True)
class ContextualizationRunResult:
    document_version: DocumentVersion
    chunks: list[Chunk]
    contextualized_chunk_count: int
    reused_contextualized_chunk_count: int
    generated_summaries: tuple[GeneratedContextualSummary, ...]


class DeterministicContextualizer:
    """Local deterministic contextualizer for offline indexing and tests."""

    provider_name = "local"
    model_name = "deterministic-context-v1"

    def __init__(self, *, max_summary_chars: int = 240) -> None:
        if max_summary_chars < 80:
            raise ContextualizationPipelineError(
                "max_summary_chars must be at least 80"
            )
        self._max_summary_chars = max_summary_chars

    def contextualize(
        self,
        request: ContextualizationRequest,
    ) -> GeneratedContextualSummary:
        title = _document_title(request.document_text)
        section = _section_heading(request.section_metadata)
        excerpt = _compact_text(request.chunk_text)
        summary = _truncate_text(
            ". ".join(
                [
                    f"Document: {title}",
                    f"Section: {section}",
                    f"Chunk {request.ordinal + 1}: {excerpt}",
                ]
            ),
            max_chars=self._max_summary_chars,
        )
        return GeneratedContextualSummary(
            chunk_id=request.chunk_id,
            summary=summary,
            metadata={
                "contextualizer_model": self.model_name,
                "contextualizer_provider": self.provider_name,
                "contextualizer_version": "contextual_summary_v1",
            },
        )


class ContextualizationPipeline:
    """Persists generated contextual summaries on existing chunks."""

    def __init__(
        self,
        session: Session,
        *,
        contextualizer: Contextualizer | None = None,
    ) -> None:
        self._chunk_repo = ChunkRepository(session)
        self._document_repo = DocumentRepository(session)
        self._contextualizer = contextualizer or DeterministicContextualizer()

    def contextualize_document_version(
        self,
        *,
        project_id: UUID,
        document_version_id: UUID,
    ) -> ContextualizationRunResult:
        document_version = self._document_repo.get_version(
            project_id=project_id,
            document_version_id=document_version_id,
        )
        if document_version is None:
            raise ContextualizationPipelineError(
                "document version does not belong to project"
            )

        chunks = self._chunk_repo.list_by_document_version(
            project_id=project_id,
            document_version_id=document_version_id,
        )
        if not chunks:
            raise ContextualizationPipelineError("document version has no chunks")

        generated: list[GeneratedContextualSummary] = []
        reused_count = 0
        for chunk in chunks:
            if _has_contextual_summary(chunk):
                reused_count += 1
                continue

            request = self._request_for_chunk(
                project_id=project_id,
                document_version=document_version,
                chunk=chunk,
            )
            output = self._contextualizer.contextualize(request)
            summary = output.summary.strip()
            if not summary:
                raise ContextualizationPipelineError(
                    "contextualizer returned empty summary"
                )
            self._chunk_repo.update_contextual_summary(
                project_id=project_id,
                chunk_id=chunk.id,
                contextual_summary=summary,
            )
            generated.append(
                GeneratedContextualSummary(
                    chunk_id=output.chunk_id,
                    summary=summary,
                    metadata=dict(output.metadata),
                )
            )

        return ContextualizationRunResult(
            document_version=document_version,
            chunks=chunks,
            contextualized_chunk_count=len(generated),
            reused_contextualized_chunk_count=reused_count,
            generated_summaries=tuple(generated),
        )

    def _request_for_chunk(
        self,
        *,
        project_id: UUID,
        document_version: DocumentVersion,
        chunk: Chunk,
    ) -> ContextualizationRequest:
        text = document_version.normalized_text
        if chunk.char_start < 0 or chunk.char_end > len(text):
            raise ContextualizationPipelineError(
                "chunk offsets are outside document text"
            )
        if chunk.char_end <= chunk.char_start:
            raise ContextualizationPipelineError("chunk offsets are empty")

        return ContextualizationRequest(
            project_id=project_id,
            document_version_id=document_version.id,
            chunk_id=chunk.id,
            ordinal=chunk.ordinal,
            document_text=text,
            chunk_text=text[chunk.char_start : chunk.char_end],
            section_metadata=chunk.section_metadata,
        )


def _has_contextual_summary(chunk: Chunk) -> bool:
    return isinstance(chunk.contextual_summary, str) and bool(
        chunk.contextual_summary.strip()
    )


def _document_title(document_text: str) -> str:
    for line in document_text.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            title = stripped.lstrip("#").strip()
            if title:
                return _compact_text(title)
    return "Untitled document"


def _section_heading(section_metadata: Mapping[str, Any] | None) -> str:
    if not section_metadata:
        return "Unsectioned"
    heading = section_metadata.get("heading")
    if isinstance(heading, str) and heading.strip():
        return _compact_text(heading)
    section_path = section_metadata.get("section_path")
    if isinstance(section_path, list):
        path = [value.strip() for value in section_path if isinstance(value, str)]
        if path:
            return _compact_text(" > ".join(path))
    return "Unsectioned"


def _compact_text(value: str) -> str:
    return " ".join(value.split())


def _truncate_text(value: str, *, max_chars: int) -> str:
    if len(value) <= max_chars:
        return value
    trimmed = value[: max_chars - 1].rstrip()
    if " " in trimmed:
        trimmed = trimmed.rsplit(" ", maxsplit=1)[0]
    return f"{trimmed}..."
