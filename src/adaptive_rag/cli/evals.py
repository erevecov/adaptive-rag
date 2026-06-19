"""Comandos CLI de evals offline."""

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
from adaptive_rag.evals import (
    EvalDatasetError,
    load_eval_suite,
    run_eval_suite,
    serialize_eval_report,
)

app = typer.Typer(no_args_is_help=True)


@app.command("run")
def run(
    suite_path: Annotated[Path, typer.Argument()],
    output: Annotated[Path | None, typer.Option("--output")] = None,
) -> None:
    try:
        suite = load_eval_suite(suite_path)
    except EvalDatasetError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(1) from exc

    with session_scope() as session:
        report = run_eval_suite(
            session,
            suite,
            provider=get_cli_dense_embedding_provider(),
            chat_runner=get_cli_chat_runner(),
        )

    payload = json.dumps(serialize_eval_report(report))
    if output is None:
        typer.echo(payload)
    else:
        output.write_text(f"{payload}\n", encoding="utf-8")

    if report.status == "failed":
        raise typer.Exit(1)
