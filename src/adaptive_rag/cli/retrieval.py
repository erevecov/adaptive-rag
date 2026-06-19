"""Comandos CLI de retrieval."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Annotated
from uuid import UUID

import typer

from adaptive_rag.db.session import session_scope
from adaptive_rag.embeddings import DenseEmbeddingProvider
from adaptive_rag.retrieval import (
    RetrievalMetadataFilter,
    RetrievalSearchRequest,
    RetrievalService,
    RetrievalServiceError,
)
from adaptive_rag.retrieval.payloads import serialize_retrieval_results
from adaptive_rag.retrieval.providers import get_default_dense_embedding_provider

app = typer.Typer(no_args_is_help=True)


def get_cli_dense_embedding_provider() -> DenseEmbeddingProvider:
    return get_default_dense_embedding_provider()


@app.command("search")
def search(
    project_id: Annotated[UUID, typer.Option("--project-id")],
    query: Annotated[str, typer.Option("--query")],
    limit: Annotated[int, typer.Option("--limit")] = 10,
    source_id: Annotated[UUID | None, typer.Option("--source-id")] = None,
    document_id: Annotated[UUID | None, typer.Option("--document-id")] = None,
    source_type: Annotated[str | None, typer.Option("--source-type")] = None,
    tag: Annotated[list[str] | None, typer.Option("--tag")] = None,
    source_created_at_from: Annotated[
        str | None,
        typer.Option("--source-created-at-from"),
    ] = None,
    source_created_at_to: Annotated[
        str | None,
        typer.Option("--source-created-at-to"),
    ] = None,
    document_created_at_from: Annotated[
        str | None,
        typer.Option("--document-created-at-from"),
    ] = None,
    document_created_at_to: Annotated[
        str | None,
        typer.Option("--document-created-at-to"),
    ] = None,
) -> None:
    metadata_filter = RetrievalMetadataFilter(
        source_id=source_id,
        document_id=document_id,
        source_type=source_type,
        tags=tuple(tag or ()),
        source_created_at_from=_parse_datetime(
            source_created_at_from,
            field_name="source_created_at_from",
        ),
        source_created_at_to=_parse_datetime(
            source_created_at_to,
            field_name="source_created_at_to",
        ),
        document_created_at_from=_parse_datetime(
            document_created_at_from,
            field_name="document_created_at_from",
        ),
        document_created_at_to=_parse_datetime(
            document_created_at_to,
            field_name="document_created_at_to",
        ),
    )
    request = RetrievalSearchRequest(
        project_id=project_id,
        query=query,
        limit=limit,
        metadata_filter=metadata_filter,
    )

    with session_scope() as session:
        service = RetrievalService(
            session,
            provider=get_cli_dense_embedding_provider(),
        )
        try:
            results = service.search(request)
        except RetrievalServiceError as exc:
            typer.echo(str(exc), err=True)
            raise typer.Exit(1) from exc

    typer.echo(json.dumps({"results": serialize_retrieval_results(results)}))


def _parse_datetime(value: str | None, *, field_name: str) -> datetime | None:
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

