"""Construccion de proyectos fixture-backed para evals offline."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.orm import Session

from adaptive_rag.db.models import EMBEDDING_DIMENSIONS
from adaptive_rag.db.repositories import (
    ChunkRepository,
    DocumentRepository,
    ProjectRepository,
    SourceRepository,
)
from adaptive_rag.embeddings import DenseEmbeddingProvider
from adaptive_rag.evals.errors import EvalDatasetError
from adaptive_rag.evals.models import EvalEvidence, EvalSuite


@dataclass(frozen=True, slots=True)
class EvalRetrievalFixtureProject:
    """Proyecto temporal construido desde una suite local."""

    project_id: UUID
    evidence_id_by_chunk_id: dict[UUID, str]
    document_version_ids: tuple[UUID, ...]


def build_retrieval_fixture_project(
    session: Session,
    suite: EvalSuite,
    *,
    provider: DenseEmbeddingProvider,
    use_contextual_summaries: bool = False,
) -> EvalRetrievalFixtureProject:
    """Persiste evidence como sources/documents/chunks para RetrievalService."""

    _validate_provider_dimensions(provider)
    project = ProjectRepository(session).create(
        name=f"eval:{suite.suite_id}",
        retrieval_contextualization_enabled=use_contextual_summaries,
    )
    source_repo = SourceRepository(session)
    document_repo = DocumentRepository(session)
    chunk_repo = ChunkRepository(session)
    embeddings = _resolve_evidence_embeddings(
        suite.evidence,
        provider=provider,
        use_contextual_summaries=use_contextual_summaries,
    )
    evidence_id_by_chunk_id: dict[UUID, str] = {}
    document_version_ids: list[UUID] = []

    for index, evidence in enumerate(suite.evidence):
        source = source_repo.create(
            project_id=project.id,
            source_type=evidence.source_type,
            external_id=evidence.source_external_id,
            tags=evidence.tags,
            extra_metadata=_source_metadata(evidence),
        )
        document = document_repo.create_document(
            project_id=project.id,
            source_id=source.id,
            stable_id=evidence.id,
        )
        version = document_repo.create_version(
            project_id=project.id,
            document_id=document.id,
            version_number=1,
            normalized_text=evidence.text,
            content_hash=_content_hash(evidence.text),
            index_fingerprint=f"eval:{suite.suite_id}:{evidence.id}",
            parser_metadata={"eval_suite_id": suite.suite_id},
            extraction_metadata={"eval_evidence_id": evidence.id},
        )
        chunk = chunk_repo.create(
            project_id=project.id,
            document_version_id=version.id,
            ordinal=0,
            char_start=0,
            char_end=len(evidence.text),
            token_count=len(evidence.text.split()),
            section_metadata={
                "eval_evidence_id": evidence.id,
                "section_path": [evidence.id],
            },
            chunker_metadata={
                "chunker_version": "eval_fixture_v1",
                "eval_suite_id": suite.suite_id,
                "eval_evidence_id": evidence.id,
            },
            contextual_summary=(
                evidence.contextual_summary if use_contextual_summaries else None
            ),
            embedding=embeddings[index],
        )
        chunk.embedding_metadata = {
            "embedding_dimensions": EMBEDDING_DIMENSIONS,
            "embedding_model": provider.model_name,
            "embedding_provider": provider.provider_name,
            "eval_evidence_id": evidence.id,
            "eval_suite_id": suite.suite_id,
        }
        evidence_id_by_chunk_id[chunk.id] = evidence.id
        document_version_ids.append(version.id)

    session.flush()
    return EvalRetrievalFixtureProject(
        project_id=project.id,
        evidence_id_by_chunk_id=evidence_id_by_chunk_id,
        document_version_ids=tuple(document_version_ids),
    )


def _resolve_evidence_embeddings(
    evidence: tuple[EvalEvidence, ...],
    *,
    provider: DenseEmbeddingProvider,
    use_contextual_summaries: bool,
) -> list[list[float]]:
    embeddings: list[list[float] | None] = [
        _validate_embedding(item.embedding, evidence_id=item.id)
        if item.embedding is not None and not use_contextual_summaries
        else None
        for item in evidence
    ]
    missing_indexes = [
        index for index, embedding in enumerate(embeddings) if embedding is None
    ]
    if missing_indexes:
        generated = provider.embed_texts(
            [
                _embedding_text(
                    evidence[index],
                    use_contextual_summary=use_contextual_summaries,
                )
                for index in missing_indexes
            ]
        )
        if len(generated) != len(missing_indexes):
            raise EvalDatasetError("eval embedding provider returned wrong count")
        for index, embedding in zip(missing_indexes, generated, strict=True):
            embeddings[index] = _validate_embedding(
                tuple(embedding),
                evidence_id=evidence[index].id,
            )
    return [embedding for embedding in embeddings if embedding is not None]


def _embedding_text(
    evidence: EvalEvidence,
    *,
    use_contextual_summary: bool,
) -> str:
    contextual_summary = evidence.contextual_summary or ""
    if use_contextual_summary and contextual_summary:
        return f"{contextual_summary}\n\n{evidence.text}"
    return evidence.text


def _validate_embedding(
    embedding: tuple[float, ...] | list[float],
    *,
    evidence_id: str,
) -> list[float]:
    values = [float(value) for value in embedding]
    if len(values) != EMBEDDING_DIMENSIONS:
        raise EvalDatasetError(
            f"{evidence_id} embedding dimension mismatch: "
            f"expected {EMBEDDING_DIMENSIONS}, got {len(values)}"
        )
    return values


def _validate_provider_dimensions(provider: DenseEmbeddingProvider) -> None:
    if provider.dimensions != EMBEDDING_DIMENSIONS:
        raise EvalDatasetError(
            "eval embedding provider dimension mismatch: "
            f"expected {EMBEDDING_DIMENSIONS}, got {provider.dimensions}"
        )


def _source_metadata(evidence: EvalEvidence) -> dict[str, object]:
    metadata = dict(evidence.metadata or {})
    metadata["eval_evidence_id"] = evidence.id
    return metadata


def _content_hash(text: str) -> str:
    return f"sha256:{hashlib.sha256(text.encode('utf-8')).hexdigest()}"
