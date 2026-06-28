"""Comandos CLI de evals offline."""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path
from typing import Annotated

import typer

from adaptive_rag.chat import QwenChatRunnerError
from adaptive_rag.cli.dependencies import (
    get_cli_chat_runner,
    get_cli_dense_embedding_provider,
    get_cli_hosted_eval_runtime,
    get_cli_sparse_embedding_provider,
)
from adaptive_rag.config.settings import get_settings
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
    run_retrieval_strategy_gate_eval_suite,
    serialize_eval_report,
    serialize_graph_live_evidence_report,
    serialize_graph_quality_gate_report,
    serialize_retrieval_strategy_gate_report,
    summarize_provider_usage,
    validate_hosted_rerank_eval_options,
)
from adaptive_rag.provider_runtime import ProviderConfigurationError
from adaptive_rag.provider_usage import (
    InMemoryProviderUsageTracker,
    ProviderBudgetExceededError,
)
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
        RetrievalStrategy | None,
        typer.Option("--retrieval-strategy"),
    ] = None,
) -> None:
    try:
        suite = load_eval_suite(suite_path)
    except EvalDatasetError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(1) from exc

    active_mode = _parse_mode(mode)
    active_retrieval_strategy: RetrievalStrategy = retrieval_strategy or (
        "dense" if active_mode == "hosted" else "dense_sparse"
    )
    try:
        if active_mode == "hosted":
            if retrieval_strategy is not None and active_retrieval_strategy != "dense":
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
                    sparse_provider=getattr(runtime, "sparse_provider", None),
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
                    sparse_provider=(
                        get_cli_sparse_embedding_provider()
                        if active_retrieval_strategy in ("sparse", "dense_sparse")
                        else None
                    ),
                    chat_runner=get_cli_chat_runner(),
                    retrieval_strategy=active_retrieval_strategy,
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


@app.command("strategy-gate")
def strategy_gate(
    suite_path: Annotated[Path, typer.Argument()],
    output: Annotated[Path | None, typer.Option("--output")] = None,
    require_live_qwen_sparse: Annotated[
        bool,
        typer.Option(
            "--require-live-qwen-sparse",
            help=(
                "Fail before running unless the strategy gate is configured "
                "for live Qwen dense+sparse embeddings."
            ),
        ),
    ] = False,
) -> None:
    try:
        suite = load_eval_suite(suite_path)
    except EvalDatasetError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(1) from exc

    try:
        if require_live_qwen_sparse:
            _validate_live_qwen_sparse_strategy_gate_config()
        usage_tracker = InMemoryProviderUsageTracker()
        with session_scope() as session:
            report = run_retrieval_strategy_gate_eval_suite(
                session,
                suite,
                provider=get_cli_dense_embedding_provider(
                    usage_tracker=usage_tracker,
                ),
                sparse_provider=get_cli_sparse_embedding_provider(
                    usage_tracker=usage_tracker,
                ),
            )
        if usage_tracker.records:
            report = replace(
                report,
                provider_usage=summarize_provider_usage(usage_tracker.records),
            )
    except (
        EvalConfigurationError,
        ProviderConfigurationError,
        QwenEmbeddingProviderError,
    ) as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(1) from exc

    payload = json.dumps(serialize_retrieval_strategy_gate_report(report))
    if output is None:
        typer.echo(payload)
    else:
        output.write_text(f"{payload}\n", encoding="utf-8")

    if report.status == "failed":
        raise typer.Exit(1)


def _validate_live_qwen_sparse_strategy_gate_config() -> None:
    settings = get_settings()
    missing: list[str] = []
    if settings.provider_runtime_mode != "live":
        missing.append("ADAPTIVE_RAG_PROVIDER_RUNTIME_MODE=live")
    if settings.embedding_provider != "qwen":
        missing.append("ADAPTIVE_RAG_EMBEDDING_PROVIDER=qwen")
    if not settings.embedding_model:
        missing.append("ADAPTIVE_RAG_EMBEDDING_MODEL")
    if settings.sparse_embedding_provider != "qwen":
        missing.append("ADAPTIVE_RAG_SPARSE_EMBEDDING_PROVIDER=qwen")
    if not settings.sparse_embedding_model:
        missing.append("ADAPTIVE_RAG_SPARSE_EMBEDDING_MODEL")
    if settings.qwen_api_key is None:
        missing.append("ADAPTIVE_RAG_QWEN_API_KEY")
    if not settings.qwen_base_url:
        missing.append("ADAPTIVE_RAG_QWEN_BASE_URL")
    if settings.provider_max_cost_usd is None:
        missing.append("ADAPTIVE_RAG_PROVIDER_MAX_COST_USD")
    elif settings.provider_max_cost_usd <= 0:
        missing.append("ADAPTIVE_RAG_PROVIDER_MAX_COST_USD>0")
    if missing:
        raise EvalConfigurationError(
            "live Qwen sparse strategy gate requires " + ", ".join(missing)
        )


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
