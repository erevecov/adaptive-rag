"""CLI contextualization reindex and A/B compare (M50)."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Annotated, Literal
from uuid import UUID

import typer
from sqlalchemy.orm import Session

from adaptive_rag.cli.dense import list_project_document_version_ids
from adaptive_rag.contextualization import (
    ContextualizationPipeline,
    ContextualizationPipelineError,
    DeterministicContextualizer,
    OptInLlmContextualizer,
)
from adaptive_rag.db.session import session_scope

app = typer.Typer(no_args_is_help=True)

ContextualizerKind = Literal["deterministic", "llm_opt_in"]


@app.command("reindex")
def reindex(
    project_id: Annotated[UUID, typer.Option("--project-id")],
    document_version_id: Annotated[
        UUID | None,
        typer.Option("--document-version-id"),
    ] = None,
    provider: Annotated[
        str,
        typer.Option(
            "--provider",
            help="deterministic (default) or llm_opt_in",
        ),
    ] = "deterministic",
    force: Annotated[
        bool,
        typer.Option(
            "--force",
            help="Regenerate summaries even when already present.",
        ),
    ] = False,
) -> None:
    """Regenerate contextual summaries for a project or one document version."""

    started = datetime.now(UTC)
    contextualizer = _build_contextualizer(provider)
    with session_scope() as session:
        version_ids = (
            [document_version_id]
            if document_version_id is not None
            else list_project_document_version_ids(session, project_id=project_id)
        )
        pipeline = ContextualizationPipeline(session, contextualizer=contextualizer)
        generated = 0
        reused = 0
        try:
            for version_id in version_ids:
                result = pipeline.contextualize_document_version(
                    project_id=project_id,
                    document_version_id=version_id,
                    force=force,
                )
                generated += result.contextualized_chunk_count
                reused += result.reused_contextualized_chunk_count
            session.commit()
        except (ContextualizationPipelineError, ValueError) as exc:
            typer.echo(str(exc), err=True)
            raise typer.Exit(1) from exc

    finished = datetime.now(UTC)
    typer.echo(
        json.dumps(
            {
                "project_id": str(project_id),
                "document_version_count": len(version_ids),
                "contextualized_chunk_count": generated,
                "reused_contextualized_chunk_count": reused,
                "provider": contextualizer.provider_name,
                "model": contextualizer.model_name,
                "force": force,
                "started_at": started.isoformat(),
                "finished_at": finished.isoformat(),
                "watermark": finished.isoformat(),
            }
        )
    )


@app.command("ab-compare")
def ab_compare(
    project_id: Annotated[UUID, typer.Option("--project-id")],
    document_version_id: Annotated[UUID, typer.Option("--document-version-id")],
) -> None:
    """Compare deterministic vs llm_opt_in summaries for one document version."""

    with session_scope() as session:
        try:
            report = compare_contextualizers(
                session,
                project_id=project_id,
                document_version_id=document_version_id,
            )
        except (ContextualizationPipelineError, ValueError) as exc:
            typer.echo(str(exc), err=True)
            raise typer.Exit(1) from exc
        session.rollback()  # A/B is observational; do not persist last provider only
    typer.echo(json.dumps(report))


def compare_contextualizers(
    session: Session,
    *,
    project_id: UUID,
    document_version_id: UUID,
) -> dict[str, object]:
    """Run both contextualizers with force and report differing summaries."""

    det = DeterministicContextualizer()
    llm = OptInLlmContextualizer()
    det_pipeline = ContextualizationPipeline(session, contextualizer=det)
    llm_pipeline = ContextualizationPipeline(session, contextualizer=llm)

    det_result = det_pipeline.contextualize_document_version(
        project_id=project_id,
        document_version_id=document_version_id,
        force=True,
    )
    # Capture det summaries before overwrite
    det_by_chunk = {
        item.chunk_id: item.summary for item in det_result.generated_summaries
    }

    llm_result = llm_pipeline.contextualize_document_version(
        project_id=project_id,
        document_version_id=document_version_id,
        force=True,
    )
    llm_by_chunk = {
        item.chunk_id: item.summary for item in llm_result.generated_summaries
    }

    chunk_ids = sorted(set(det_by_chunk) | set(llm_by_chunk), key=str)
    differing = 0
    for chunk_id in chunk_ids:
        if det_by_chunk.get(chunk_id) != llm_by_chunk.get(chunk_id):
            differing += 1

    return {
        "project_id": str(project_id),
        "document_version_id": str(document_version_id),
        "chunk_count": len(chunk_ids),
        "differing_summary_count": differing,
        "deterministic_provider": det.provider_name,
        "llm_opt_in_provider": llm.provider_name,
        "identical": differing == 0,
    }


def _build_contextualizer(
    provider: str,
) -> DeterministicContextualizer | OptInLlmContextualizer:
    kind = provider.strip().lower()
    if kind in {"deterministic", "local", "fake"}:
        return DeterministicContextualizer()
    if kind in {"llm_opt_in", "llm"}:
        return OptInLlmContextualizer()
    raise typer.BadParameter("provider must be deterministic or llm_opt_in")
