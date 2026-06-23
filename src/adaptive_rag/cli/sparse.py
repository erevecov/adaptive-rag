"""Comandos CLI para sparse embeddings opt-in."""

from __future__ import annotations

import json
from typing import Annotated
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
)

app = typer.Typer(no_args_is_help=True)


@app.command("backfill")
def backfill(
    project_id: Annotated[UUID, typer.Option("--project-id")],
    document_version_id: Annotated[
        UUID | None,
        typer.Option("--document-version-id"),
    ] = None,
) -> None:
    with session_scope() as session:
        version_ids = (
            [document_version_id]
            if document_version_id is not None
            else _list_project_document_version_ids(session, project_id=project_id)
        )
        pipeline = SparseEmbeddingPipeline(
            session,
            provider=get_cli_sparse_embedding_provider(),
        )
        embedded_count = 0
        reused_count = 0
        try:
            for version_id in version_ids:
                result = pipeline.embed_document_version(
                    project_id=project_id,
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
                "project_id": str(project_id),
                "document_version_count": len(version_ids),
                "embedded_chunk_count": embedded_count,
                "reused_chunk_count": reused_count,
            }
        )
    )


def _list_project_document_version_ids(
    session: Session,
    *,
    project_id: UUID,
) -> list[UUID]:
    statement = (
        select(DocumentVersion.id)
        .join(Document, DocumentVersion.document_id == Document.id)
        .where(Document.project_id == project_id)
        .order_by(
            Document.created_at,
            DocumentVersion.version_number,
            DocumentVersion.id,
        )
    )
    return list(session.scalars(statement))
