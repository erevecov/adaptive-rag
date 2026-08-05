"""CLI dense reindex by project with JSON report (M50)."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

import typer
from sqlalchemy import select
from sqlalchemy.orm import Session

from adaptive_rag.cli.dependencies import get_cli_dense_embedding_provider
from adaptive_rag.db.models import Document, DocumentVersion
from adaptive_rag.db.session import session_scope
from adaptive_rag.embeddings import DenseEmbeddingPipeline, DenseEmbeddingPipelineError

app = typer.Typer(no_args_is_help=True)


@app.command("reindex")
def reindex(
    project_id: Annotated[UUID, typer.Option("--project-id")],
    document_version_id: Annotated[
        UUID | None,
        typer.Option("--document-version-id"),
    ] = None,
    force: Annotated[
        bool,
        typer.Option(
            "--force",
            help="Re-embed even when current dense embeddings match.",
        ),
    ] = False,
) -> None:
    """Recompute dense embeddings for a project (or one document version)."""

    started = datetime.now(UTC)
    with session_scope() as session:
        version_ids = (
            [document_version_id]
            if document_version_id is not None
            else list_project_document_version_ids(session, project_id=project_id)
        )
        pipeline = DenseEmbeddingPipeline(
            session,
            provider=get_cli_dense_embedding_provider(),
        )
        embedded_count = 0
        reused_count = 0
        try:
            for version_id in version_ids:
                result = pipeline.embed_document_version(
                    project_id=project_id,
                    document_version_id=version_id,
                    force=force,
                )
                embedded_count += result.embedded_chunk_count
                reused_count += result.reused_chunk_count
            session.commit()
        except (DenseEmbeddingPipelineError, ValueError) as exc:
            typer.echo(str(exc), err=True)
            raise typer.Exit(1) from exc

    finished = datetime.now(UTC)
    typer.echo(
        json.dumps(
            {
                "project_id": str(project_id),
                "document_version_count": len(version_ids),
                "embedded_chunk_count": embedded_count,
                "reused_chunk_count": reused_count,
                "force": force,
                "started_at": started.isoformat(),
                "finished_at": finished.isoformat(),
                "watermark": finished.isoformat(),
            }
        )
    )


def list_project_document_version_ids(
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


# Back-compat alias used by unit tests / callers.
_list_project_document_version_ids = list_project_document_version_ids
