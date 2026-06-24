"""Comandos CLI de acceptance end-to-end."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer

from adaptive_rag.acceptance import (
    DEFAULT_ACCEPTANCE_CONTENT,
    DEFAULT_ACCEPTANCE_PROJECT_NAME,
    DEFAULT_ACCEPTANCE_SOURCE_EXTERNAL_ID,
    DEFAULT_ACCEPTANCE_WORKER_ID,
    AcceptanceError,
    run_runtime_settings_acceptance_smoke,
    runtime_settings_acceptance_report_payload,
)
from adaptive_rag.db.session import session_scope
from adaptive_rag.first_run import DEFAULT_QUESTION

app = typer.Typer(no_args_is_help=True)


@app.command("runtime-settings-smoke")
def runtime_settings_smoke(
    project_name: Annotated[
        str,
        typer.Option("--project-name"),
    ] = DEFAULT_ACCEPTANCE_PROJECT_NAME,
    source_external_id: Annotated[
        str,
        typer.Option("--source-external-id"),
    ] = DEFAULT_ACCEPTANCE_SOURCE_EXTERNAL_ID,
    content: Annotated[
        str,
        typer.Option("--content"),
    ] = DEFAULT_ACCEPTANCE_CONTENT,
    question: Annotated[
        str,
        typer.Option("--question"),
    ] = DEFAULT_QUESTION,
    worker_id: Annotated[
        str,
        typer.Option("--worker-id"),
    ] = DEFAULT_ACCEPTANCE_WORKER_ID,
    output: Annotated[
        Path | None,
        typer.Option("--output"),
    ] = None,
) -> None:
    with session_scope() as session:
        try:
            report = run_runtime_settings_acceptance_smoke(
                session,
                project_name=project_name,
                source_external_id=source_external_id,
                content=content,
                question=question,
                worker_id=worker_id,
            )
        except AcceptanceError as exc:
            session.rollback()
            typer.echo(str(exc), err=True)
            raise typer.Exit(1) from exc
        session.commit()
        payload = json.dumps(runtime_settings_acceptance_report_payload(report))

    if output is None:
        typer.echo(payload)
    else:
        output.write_text(f"{payload}\n", encoding="utf-8")

    if report.status != "succeeded":
        raise typer.Exit(1)
