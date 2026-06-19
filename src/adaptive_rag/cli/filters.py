"""Construccion de filtros compartida por comandos CLI."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

import typer

from adaptive_rag.retrieval import RetrievalMetadataFilter


def build_retrieval_metadata_filter(
    *,
    source_id: UUID | None,
    document_id: UUID | None,
    source_type: str | None,
    tag: list[str] | None,
    source_created_at_from: str | None,
    source_created_at_to: str | None,
    document_created_at_from: str | None,
    document_created_at_to: str | None,
) -> RetrievalMetadataFilter:
    return RetrievalMetadataFilter(
        source_id=source_id,
        document_id=document_id,
        source_type=source_type,
        tags=tuple(tag or ()),
        source_created_at_from=parse_cli_datetime(
            source_created_at_from,
            field_name="source_created_at_from",
        ),
        source_created_at_to=parse_cli_datetime(
            source_created_at_to,
            field_name="source_created_at_to",
        ),
        document_created_at_from=parse_cli_datetime(
            document_created_at_from,
            field_name="document_created_at_from",
        ),
        document_created_at_to=parse_cli_datetime(
            document_created_at_to,
            field_name="document_created_at_to",
        ),
    )


def parse_cli_datetime(value: str | None, *, field_name: str) -> datetime | None:
    if value is None:
        return None
    normalized = value.strip()
    if not normalized:
        raise typer.BadParameter(f"{field_name} must not be empty")
    if normalized.endswith("Z"):
        normalized = f"{normalized[:-1]}+00:00"
    try:
        return datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise typer.BadParameter(f"{field_name} must be ISO 8601") from exc
