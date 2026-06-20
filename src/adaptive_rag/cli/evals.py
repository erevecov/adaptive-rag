"""Comandos CLI de evals offline."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer

from adaptive_rag.chat import QwenChatRunnerError
from adaptive_rag.cli.dependencies import (
    get_cli_chat_runner,
    get_cli_dense_embedding_provider,
    get_cli_hosted_eval_runtime,
)
from adaptive_rag.db.session import session_scope
from adaptive_rag.embeddings import QwenEmbeddingProviderError
from adaptive_rag.evals import (
    EvalConfigurationError,
    EvalDatasetError,
    EvalRunMode,
    load_eval_suite,
    run_eval_suite,
    run_hosted_eval_suite,
    serialize_eval_report,
)
from adaptive_rag.provider_runtime import ProviderConfigurationError
from adaptive_rag.provider_usage import ProviderBudgetExceededError

app = typer.Typer(no_args_is_help=True)


@app.command("run")
def run(
    suite_path: Annotated[Path, typer.Argument()],
    output: Annotated[Path | None, typer.Option("--output")] = None,
    mode: Annotated[str, typer.Option("--mode")] = "offline",
    provider: Annotated[str, typer.Option("--provider")] = "qwen",
    max_cost_usd: Annotated[float | None, typer.Option("--max-cost-usd")] = None,
) -> None:
    try:
        suite = load_eval_suite(suite_path)
    except EvalDatasetError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(1) from exc

    active_mode = _parse_mode(mode)
    try:
        if active_mode == "hosted":
            runtime = get_cli_hosted_eval_runtime(
                provider_name=provider,
                max_cost_usd=max_cost_usd,
            )
            with session_scope() as session:
                report = run_hosted_eval_suite(
                    session,
                    suite,
                    provider=runtime.provider,
                    runner=runtime.chat_runner,
                    usage_tracker=runtime.usage_tracker,
                    options=runtime.options,
                )
        else:
            with session_scope() as session:
                report = run_eval_suite(
                    session,
                    suite,
                    provider=get_cli_dense_embedding_provider(),
                    chat_runner=get_cli_chat_runner(),
                )
    except (
        EvalConfigurationError,
        ProviderBudgetExceededError,
        ProviderConfigurationError,
        QwenChatRunnerError,
        QwenEmbeddingProviderError,
    ) as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(1) from exc

    payload = json.dumps(serialize_eval_report(report))
    if output is None:
        typer.echo(payload)
    else:
        output.write_text(f"{payload}\n", encoding="utf-8")

    if report.status == "failed":
        raise typer.Exit(1)


def _parse_mode(value: str) -> EvalRunMode:
    if value == "offline":
        return "offline"
    if value == "hosted":
        return "hosted"
    raise typer.BadParameter("mode must be one of: offline, hosted")
