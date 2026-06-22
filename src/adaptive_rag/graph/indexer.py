"""Project graph projection built from canonical Postgres state."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Protocol
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from adaptive_rag.db.models import Chunk, Document, DocumentVersion, Project, Source
from adaptive_rag.db.session import session_scope
from adaptive_rag.graph.store import GraphStoreQueryError

GraphProperties = dict[str, Any]


@dataclass(frozen=True, slots=True)
class Neo4jProjectGraph:
    """Serializable graph payload for one project-scoped Neo4j rebuild."""

    project: GraphProperties
    sources: tuple[GraphProperties, ...]
    documents: tuple[GraphProperties, ...]
    document_versions: tuple[GraphProperties, ...]
    chunks: tuple[GraphProperties, ...]
    chunk_links: tuple[GraphProperties, ...]


class ProjectGraphLoader(Protocol):
    """Loads canonical project graph facts from durable storage."""

    def __call__(self, project_id: UUID) -> Neo4jProjectGraph:
        """Return a deterministic project graph payload."""


def load_project_graph(session: Session, project_id: UUID) -> Neo4jProjectGraph:
    """Build a deterministic Neo4j projection payload from Postgres rows."""

    project = session.get(Project, project_id)
    if project is None:
        raise GraphStoreQueryError("project graph source data not found")

    sources = list(
        session.scalars(
            select(Source)
            .where(Source.project_id == project_id)
            .order_by(Source.created_at, Source.external_id, Source.id)
        )
    )
    documents = list(
        session.scalars(
            select(Document)
            .where(Document.project_id == project_id)
            .order_by(Document.created_at, Document.stable_id, Document.id)
        )
    )
    document_versions = list(
        session.scalars(
            select(DocumentVersion)
            .join(Document, DocumentVersion.document_id == Document.id)
            .where(Document.project_id == project_id)
            .order_by(
                Document.stable_id,
                DocumentVersion.version_number,
                DocumentVersion.id,
            )
        )
    )
    chunks = list(
        session.scalars(
            select(Chunk)
            .join(DocumentVersion, Chunk.document_version_id == DocumentVersion.id)
            .join(Document, DocumentVersion.document_id == Document.id)
            .where(Document.project_id == project_id)
            .order_by(Document.stable_id, DocumentVersion.version_number, Chunk.ordinal)
        )
    )
    chunk_ids = {chunk.id for chunk in chunks}

    return Neo4jProjectGraph(
        project=_project_properties(project),
        sources=tuple(_source_properties(source) for source in sources),
        documents=tuple(_document_properties(document) for document in documents),
        document_versions=tuple(
            _document_version_properties(version, project_id=project_id)
            for version in document_versions
        ),
        chunks=tuple(
            _chunk_properties(chunk, project_id=project_id) for chunk in chunks
        ),
        chunk_links=tuple(
            {
                "from_chunk_id": str(chunk.id),
                "to_chunk_id": str(chunk.next_chunk_id),
            }
            for chunk in chunks
            if chunk.next_chunk_id is not None and chunk.next_chunk_id in chunk_ids
        ),
    )


def load_project_graph_from_database(project_id: UUID) -> Neo4jProjectGraph:
    """Default loader used by runtime-created Neo4j graph stores."""

    with session_scope() as session:
        return load_project_graph(session, project_id)


def _project_properties(project: Project) -> GraphProperties:
    project_id = str(project.id)
    return {
        "id": project_id,
        "project_id": project_id,
        "name": project.name,
        "embedding_mode": project.embedding_mode,
        "retrieval_contextualization_enabled": (
            project.retrieval_contextualization_enabled
        ),
        "budget_config_json": _json_or_none(project.budget_config_json),
    }


def _source_properties(source: Source) -> GraphProperties:
    return {
        "id": str(source.id),
        "project_id": str(source.project_id),
        "source_type": source.source_type,
        "external_id": source.external_id,
        "tags": list(source.tags or []),
        "extra_metadata_json": _json_or_none(source.extra_metadata),
    }


def _document_properties(document: Document) -> GraphProperties:
    return {
        "id": str(document.id),
        "project_id": str(document.project_id),
        "source_id": str(document.source_id),
        "stable_id": document.stable_id,
    }


def _document_version_properties(
    version: DocumentVersion,
    *,
    project_id: UUID,
) -> GraphProperties:
    return {
        "id": str(version.id),
        "project_id": str(project_id),
        "document_id": str(version.document_id),
        "version_number": version.version_number,
        "content_hash": version.content_hash,
        "index_fingerprint": version.index_fingerprint,
        "parser_metadata_json": _json_or_none(version.parser_metadata),
        "extraction_metadata_json": _json_or_none(version.extraction_metadata),
    }


def _chunk_properties(chunk: Chunk, *, project_id: UUID) -> GraphProperties:
    return {
        "id": str(chunk.id),
        "project_id": str(project_id),
        "document_version_id": str(chunk.document_version_id),
        "ordinal": chunk.ordinal,
        "char_start": chunk.char_start,
        "char_end": chunk.char_end,
        "token_count": chunk.token_count,
        "section_metadata_json": _json_or_none(chunk.section_metadata),
        "chunker_metadata_json": _json_or_none(chunk.chunker_metadata),
        "embedding_metadata_json": _json_or_none(chunk.embedding_metadata),
        "contextual_summary": chunk.contextual_summary,
    }


def _json_or_none(value: dict[str, Any] | None) -> str | None:
    if value is None:
        return None
    return json.dumps(value, sort_keys=True, separators=(",", ":"))
