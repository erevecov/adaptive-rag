"""Comandos CLI de retrieval."""

from __future__ import annotations

import json
from typing import Annotated
from uuid import UUID

import typer

from adaptive_rag.cli.dependencies import (
    get_cli_dense_embedding_provider,
    get_cli_rerank_provider,
)
from adaptive_rag.cli.filters import build_retrieval_metadata_filter
from adaptive_rag.db.session import session_scope
from adaptive_rag.retrieval import (
    RetrievalRerankOptions,
    RetrievalSearchRequest,
    RetrievalService,
    RetrievalServiceError,
)
from adaptive_rag.retrieval.payloads import serialize_retrieval_results

app = typer.Typer(no_args_is_help=True)


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
    rerank_candidate_limit: Annotated[
        int | None,
        typer.Option("--rerank-candidate-limit"),
    ] = None,
) -> None:
    try:
        rerank_options = _build_rerank_options(
            limit=limit,
            candidate_limit=rerank_candidate_limit,
        )
    except RetrievalServiceError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(1) from exc

    metadata_filter = build_retrieval_metadata_filter(
        source_id=source_id,
        document_id=document_id,
        source_type=source_type,
        tag=tag,
        source_created_at_from=source_created_at_from,
        source_created_at_to=source_created_at_to,
        document_created_at_from=document_created_at_from,
        document_created_at_to=document_created_at_to,
    )
    request = RetrievalSearchRequest(
        project_id=project_id,
        query=query,
        limit=limit,
        metadata_filter=metadata_filter,
        rerank=rerank_options,
    )

    with session_scope() as session:
        service = RetrievalService(
            session,
            provider=get_cli_dense_embedding_provider(),
            reranker=get_cli_rerank_provider() if rerank_options is not None else None,
        )
        try:
            results = service.search(request)
        except RetrievalServiceError as exc:
            typer.echo(str(exc), err=True)
            raise typer.Exit(1) from exc

    typer.echo(json.dumps({"results": serialize_retrieval_results(results)}))


def _build_rerank_options(
    *,
    limit: int,
    candidate_limit: int | None,
) -> RetrievalRerankOptions | None:
    if candidate_limit is None:
        return None
    if candidate_limit <= 0:
        raise RetrievalServiceError("rerank candidate_limit must be positive")
    if candidate_limit < limit:
        raise RetrievalServiceError(
            "rerank candidate_limit must be greater than or equal to limit"
        )
    return RetrievalRerankOptions(candidate_limit=candidate_limit)

