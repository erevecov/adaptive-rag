"""Comandos CLI para sparse embeddings opt-in."""

from __future__ import annotations

import json
from inspect import signature
from typing import Annotated, Any, cast
from uuid import UUID

import typer
from sqlalchemy import select
from sqlalchemy.orm import Session

from adaptive_rag.cli.dependencies import get_cli_sparse_embedding_provider
from adaptive_rag.db.models import Document, DocumentVersion
from adaptive_rag.db.session import session_scope
from adaptive_rag.embeddings import (
    SparseEmbeddingPipeline,
    SparseEmbeddingPipelineError,
    SparseEmbeddingProvider,
)

app = typer.Typer(no_args_is_help=True)


@app.command("backfill")
def backfill(
    workspace_id: Annotated[UUID, typer.Option("--workspace-id")],
    document_version_id: Annotated[
        UUID | None,
        typer.Option("--document-version-id"),
    ] = None,
) -> None:
    with session_scope() as session:
        version_ids = (
            [document_version_id]
            if document_version_id is not None
            else _list_workspace_document_version_ids(
                session, workspace_id=workspace_id
            )
        )
        pipeline = SparseEmbeddingPipeline(
            session,
            provider=_get_sparse_embedding_provider(
                workspace_id=workspace_id,
                session=session,
            ),
        )
        embedded_count = 0
        reused_count = 0
        try:
            for version_id in version_ids:
                result = pipeline.embed_document_version(
                    workspace_id=workspace_id,
                    document_version_id=version_id,
                )
                embedded_count += result.embedded_chunk_count
                reused_count += result.reused_chunk_count
        except (SparseEmbeddingPipelineError, ValueError) as exc:
            typer.echo(str(exc), err=True)
            raise typer.Exit(1) from exc

    typer.echo(
        json.dumps(
            {
                "workspace_id": str(workspace_id),
                "document_version_count": len(version_ids),
                "embedded_chunk_count": embedded_count,
                "reused_chunk_count": reused_count,
            }
        )
    )


def _list_workspace_document_version_ids(
    session: Session,
    *,
    workspace_id: UUID,
) -> list[UUID]:
    statement = (
        select(DocumentVersion.id)
        .join(Document, DocumentVersion.document_id == Document.id)
        .where(Document.workspace_id == workspace_id)
        .order_by(
            Document.created_at,
            DocumentVersion.version_number,
            DocumentVersion.id,
        )
    )
    return list(session.scalars(statement))


def _get_sparse_embedding_provider(
    *,
    workspace_id: UUID,
    session: Session,
) -> SparseEmbeddingProvider:
    parameters = signature(get_cli_sparse_embedding_provider).parameters
    kwargs: dict[str, object] = {}
    if "workspace_id" in parameters:
        kwargs["workspace_id"] = workspace_id
    if "session" in parameters:
        kwargs["session"] = session
    return cast(
        SparseEmbeddingProvider,
        cast(Any, get_cli_sparse_embedding_provider)(**kwargs),
    )
