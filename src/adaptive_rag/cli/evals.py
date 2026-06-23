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
    GraphOperationalCost,
    build_graph_live_evidence_report,
    load_eval_suite,
    load_graph_operation_report,
    load_graph_retrieval_smoke_report,
    run_eval_suite,
    run_graph_quality_gate_eval_suite,
    run_hosted_eval_suite,
    serialize_eval_report,
    serialize_graph_live_evidence_report,
    serialize_graph_quality_gate_report,
    validate_hosted_rerank_eval_options,
)
from adaptive_rag.provider_runtime import ProviderConfigurationError
from adaptive_rag.provider_usage import ProviderBudgetExceededError
from adaptive_rag.retrieval import RetrievalStrategy

app = typer.Typer(no_args_is_help=True)


@app.command("run")
def run(
    suite_path: Annotated[Path, typer.Argument()],
    output: Annotated[Path | None, typer.Option("--output")] = None,
    mode: Annotated[str, typer.Option("--mode")] = "offline",
    provider: Annotated[str, typer.Option("--provider")] = "qwen",
    max_cost_usd: Annotated[float | None, typer.Option("--max-cost-usd")] = None,
    rerank_candidate_limit: Annotated[
        int | None,
        typer.Option("--rerank-candidate-limit"),
    ] = None,
    retrieval_strategy: Annotated[
        RetrievalStrategy,
        typer.Option("--retrieval-strategy"),
    ] = "dense",
) -> None:
    try:
        suite = load_eval_suite(suite_path)
    except EvalDatasetError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(1) from exc

    active_mode = _parse_mode(mode)
    try:
        if active_mode == "hosted":
            if retrieval_strategy != "dense":
                raise EvalConfigurationError(
                    "retrieval strategy selection is only supported in offline mode"
                )
            validate_hosted_rerank_eval_options(
                suite,
                rerank_candidate_limit=rerank_candidate_limit,
            )
            runtime = get_cli_hosted_eval_runtime(
                provider_name=provider,
                max_cost_usd=max_cost_usd,
                include_reranker=rerank_candidate_limit is not None,
            )
            with session_scope() as session:
                report = run_hosted_eval_suite(
                    session,
                    suite,
                    provider=runtime.provider,
                    runner=runtime.chat_runner,
                    reranker=runtime.reranker,
                    rerank_candidate_limit=rerank_candidate_limit,
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
                    retrieval_strategy=retrieval_strategy,
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


@app.command("graph-quality-gate")
def graph_quality_gate(
    suite_path: Annotated[Path, typer.Argument()],
    output: Annotated[Path | None, typer.Option("--output")] = None,
) -> None:
    try:
        suite = load_eval_suite(suite_path)
    except EvalDatasetError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(1) from exc

    try:
        with session_scope() as session:
            report = run_graph_quality_gate_eval_suite(
                session,
                suite,
                provider=get_cli_dense_embedding_provider(),
            )
    except (EvalConfigurationError, QwenEmbeddingProviderError) as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(1) from exc

    payload = json.dumps(serialize_graph_quality_gate_report(report))
    if output is None:
        typer.echo(payload)
    else:
        output.write_text(f"{payload}\n", encoding="utf-8")

    if report.status == "failed":
        raise typer.Exit(1)


@app.command("graph-live-evidence")
def graph_live_evidence(
    suite_path: Annotated[Path, typer.Argument()],
    output: Annotated[Path | None, typer.Option("--output")] = None,
    operation_report: Annotated[
        list[Path] | None,
        typer.Option("--operation-report"),
    ] = None,
    retrieval_smoke_report: Annotated[
        list[Path] | None,
        typer.Option("--retrieval-smoke-report"),
    ] = None,
    graph_operational_cost_usd: Annotated[
        float | None,
        typer.Option("--graph-operational-cost-usd"),
    ] = None,
    graph_operational_cost_notes: Annotated[
        str | None,
        typer.Option("--graph-operational-cost-notes"),
    ] = None,
) -> None:
    try:
        suite = load_eval_suite(suite_path)
        operation_reports = tuple(
            load_graph_operation_report(path) for path in operation_report or ()
        )
        retrieval_reports = tuple(
            load_graph_retrieval_smoke_report(path)
            for path in retrieval_smoke_report or ()
        )
    except EvalDatasetError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(1) from exc

    try:
        with session_scope() as session:
            quality_report = run_graph_quality_gate_eval_suite(
                session,
                suite,
                provider=get_cli_dense_embedding_provider(),
            )
        report = build_graph_live_evidence_report(
            quality_report=quality_report,
            operation_reports=operation_reports,
            retrieval_smoke_reports=retrieval_reports,
            graph_operational_cost=GraphOperationalCost(
                amount_usd=graph_operational_cost_usd,
                notes=graph_operational_cost_notes,
            ),
        )
    except (EvalConfigurationError, QwenEmbeddingProviderError) as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(1) from exc

    payload = json.dumps(serialize_graph_live_evidence_report(report))
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
