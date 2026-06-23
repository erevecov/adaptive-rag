"""Comandos CLI para el gate final de v1."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer

from adaptive_rag.cli.dependencies import (
    get_cli_chat_runner,
    get_cli_dense_embedding_provider,
)
from adaptive_rag.db.session import session_scope
from adaptive_rag.first_run import (
    DEFAULT_CONTENT,
    DEFAULT_PROJECT_NAME,
    DEFAULT_QUESTION,
    DEFAULT_SOURCE_EXTERNAL_ID,
    DEFAULT_WORKER_ID,
    FirstRunError,
)
from adaptive_rag.v1_quality_gate import (
    run_v1_quality_gate,
    v1_quality_gate_report_payload,
)

app = typer.Typer(no_args_is_help=True)


@app.command("quality-gate")
def quality_gate(
    project_name: Annotated[
        str,
        typer.Option("--project-name"),
    ] = DEFAULT_PROJECT_NAME,
    source_external_id: Annotated[
        str,
        typer.Option("--source-external-id"),
    ] = DEFAULT_SOURCE_EXTERNAL_ID,
    content: Annotated[
        str,
        typer.Option("--content"),
    ] = DEFAULT_CONTENT,
    question: Annotated[
        str,
        typer.Option("--question"),
    ] = DEFAULT_QUESTION,
    worker_id: Annotated[
        str,
        typer.Option("--worker-id"),
    ] = DEFAULT_WORKER_ID,
    output: Annotated[
        Path | None,
        typer.Option("--output"),
    ] = None,
) -> None:
    with session_scope() as session:
        try:
            report = run_v1_quality_gate(
                session,
                dense_embedding_provider=get_cli_dense_embedding_provider(),
                chat_runner=get_cli_chat_runner(),
                project_name=project_name,
                source_external_id=source_external_id,
                content=content,
                question=question,
                worker_id=worker_id,
            )
        except FirstRunError as exc:
            session.rollback()
            typer.echo(str(exc), err=True)
            raise typer.Exit(1) from exc
        session.commit()
        payload = json.dumps(v1_quality_gate_report_payload(report))

    if output is None:
        typer.echo(payload)
    else:
        output.write_text(f"{payload}\n", encoding="utf-8")

    if report.status != "succeeded":
        raise typer.Exit(1)
