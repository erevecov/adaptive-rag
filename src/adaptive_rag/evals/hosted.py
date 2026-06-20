"""Contrato inicial para evals hosted opt-in."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass, replace

from sqlalchemy.orm import Session

from adaptive_rag.chat import ChatRunner
from adaptive_rag.embeddings import DenseEmbeddingProvider
from adaptive_rag.evals.chat_runner import run_chat_eval_suite
from adaptive_rag.evals.errors import EvalConfigurationError
from adaptive_rag.evals.fixtures import build_retrieval_fixture_project
from adaptive_rag.evals.models import (
    EvalProviderUsageOperationSummary,
    EvalProviderUsageSummary,
    EvalRunOptions,
    EvalRunReport,
    EvalStatus,
    EvalSuite,
)
from adaptive_rag.evals.retrieval_comparison import (
    build_rerank_case_comparisons,
    build_rerank_comparison_metrics,
)
from adaptive_rag.evals.retrieval_runner import run_retrieval_eval_suite
from adaptive_rag.evals.runner import run_eval_suite
from adaptive_rag.provider_usage import (
    InMemoryProviderUsageTracker,
    ProviderCallRecord,
    ProviderOperation,
)
from adaptive_rag.rerank import RerankProvider
from adaptive_rag.retrieval import RetrievalRerankOptions

SUPPORTED_HOSTED_EVAL_PROVIDERS = ("qwen",)


def validate_hosted_eval_options(
    options: EvalRunOptions,
    *,
    supported_providers: tuple[str, ...] = SUPPORTED_HOSTED_EVAL_PROVIDERS,
) -> EvalRunOptions:
    """Valida opciones de hosted evals antes de construir providers live."""

    if not options.is_hosted():
        return options
    if options.max_cost_usd is None:
        raise EvalConfigurationError("hosted evals require --max-cost-usd")
    if options.max_cost_usd <= 0:
        raise EvalConfigurationError("--max-cost-usd must be greater than 0")
    if options.provider not in supported_providers:
        raise EvalConfigurationError(
            f"unsupported hosted eval provider: {options.provider}"
        )
    return options


def validate_hosted_eval_credentials(
    options: EvalRunOptions,
    *,
    qwen_api_key: object | None,
    qwen_base_url: str | None,
) -> EvalRunOptions:
    """Valida credenciales requeridas sin instanciar clientes ni llamar red."""

    validate_hosted_eval_options(options)
    if not options.is_hosted() or options.provider != "qwen":
        return options
    if qwen_api_key is None:
        raise EvalConfigurationError(
            "hosted eval provider qwen requires ADAPTIVE_RAG_QWEN_API_KEY"
        )
    if not qwen_base_url:
        raise EvalConfigurationError(
            "hosted eval provider qwen requires ADAPTIVE_RAG_QWEN_BASE_URL"
        )
    return options


def validate_hosted_rerank_eval_options(
    suite: EvalSuite,
    *,
    rerank_candidate_limit: int | None,
) -> None:
    if rerank_candidate_limit is None:
        return
    if rerank_candidate_limit <= 0:
        raise EvalConfigurationError("rerank candidate_limit must be positive")
    max_limit = max((case.limit for case in suite.retrieval_cases), default=0)
    if rerank_candidate_limit < max_limit:
        raise EvalConfigurationError(
            "rerank candidate_limit must be greater than or equal to every "
            "retrieval case limit"
        )


def run_hosted_retrieval_eval_suite(
    session: Session,
    suite: EvalSuite,
    *,
    provider: DenseEmbeddingProvider,
    reranker: RerankProvider | None = None,
    rerank_candidate_limit: int | None = None,
    usage_tracker: InMemoryProviderUsageTracker,
    options: EvalRunOptions,
) -> EvalRunReport:
    """Ejecuta retrieval hosted y agrega usage/cost al reporte."""

    validate_hosted_eval_options(options)
    if not options.is_hosted():
        raise EvalConfigurationError("hosted retrieval evals require hosted mode")
    _validate_rerank_candidate_limit(
        suite,
        reranker=reranker,
        rerank_candidate_limit=rerank_candidate_limit,
    )

    fixture_project = build_retrieval_fixture_project(
        session,
        suite,
        provider=provider,
    )
    dense_report = run_retrieval_eval_suite(
        session,
        suite,
        provider=provider,
        fixture_project=fixture_project,
    )
    if rerank_candidate_limit is None:
        return replace(
            dense_report,
            mode="hosted",
            provider_usage=summarize_provider_usage(usage_tracker.records),
        )

    reranked_report = run_retrieval_eval_suite(
        session,
        suite,
        provider=provider,
        reranker=reranker,
        rerank_options=RetrievalRerankOptions(
            candidate_limit=rerank_candidate_limit
        ),
        fixture_project=fixture_project,
    )
    comparison_cases = build_rerank_case_comparisons(
        suite=suite,
        dense_report=dense_report,
        reranked_report=reranked_report,
    )
    return replace(
        reranked_report,
        mode="hosted",
        comparison_metrics=build_rerank_comparison_metrics(
            dense_report=dense_report,
            reranked_report=reranked_report,
            comparison_cases=comparison_cases,
        ),
        comparison_cases=comparison_cases,
        provider_usage=summarize_provider_usage(usage_tracker.records),
    )


def run_hosted_eval_suite(
    session: Session,
    suite: EvalSuite,
    *,
    provider: DenseEmbeddingProvider,
    runner: ChatRunner,
    reranker: RerankProvider | None = None,
    rerank_candidate_limit: int | None = None,
    usage_tracker: InMemoryProviderUsageTracker,
    options: EvalRunOptions,
) -> EvalRunReport:
    """Ejecuta retrieval+chat hosted y agrega usage/cost al reporte."""

    validate_hosted_eval_options(options)
    if not options.is_hosted():
        raise EvalConfigurationError("hosted evals require hosted mode")
    if rerank_candidate_limit is None:
        report = run_eval_suite(
            session,
            suite,
            provider=provider,
            chat_runner=runner,
        )
        return replace(
            report,
            mode="hosted",
            provider_usage=summarize_provider_usage(usage_tracker.records),
        )

    retrieval_report = run_hosted_retrieval_eval_suite(
        session,
        suite,
        provider=provider,
        reranker=reranker,
        rerank_candidate_limit=rerank_candidate_limit,
        usage_tracker=usage_tracker,
        options=options,
    )
    chat_report = run_chat_eval_suite(
        session,
        suite,
        provider=provider,
        runner=runner,
    )
    status: EvalStatus = (
        "passed"
        if retrieval_report.status == "passed" and chat_report.status == "passed"
        else "failed"
    )
    return EvalRunReport(
        suite_id=suite.suite_id,
        status=status,
        metrics={
            **retrieval_report.metrics,
            **chat_report.metrics,
        },
        thresholds={
            **retrieval_report.thresholds,
            **chat_report.thresholds,
        },
        cases=(*retrieval_report.cases, *chat_report.cases),
        mode="hosted",
        comparison_metrics=retrieval_report.comparison_metrics,
        comparison_cases=retrieval_report.comparison_cases,
        provider_usage=summarize_provider_usage(usage_tracker.records),
    )


def run_hosted_chat_eval_suite(
    session: Session,
    suite: EvalSuite,
    *,
    provider: DenseEmbeddingProvider,
    runner: ChatRunner,
    usage_tracker: InMemoryProviderUsageTracker,
    options: EvalRunOptions,
) -> EvalRunReport:
    """Ejecuta chat hosted y agrega usage/cost al reporte."""

    validate_hosted_eval_options(options)
    if not options.is_hosted():
        raise EvalConfigurationError("hosted chat evals require hosted mode")

    report = run_chat_eval_suite(
        session,
        suite,
        provider=provider,
        runner=runner,
    )
    return replace(
        report,
        mode="hosted",
        provider_usage=summarize_provider_usage(usage_tracker.records),
    )


def summarize_provider_usage(
    records: Iterable[ProviderCallRecord],
) -> EvalProviderUsageSummary:
    """Agrega registros live en un resumen estable y serializable."""

    groups: dict[_UsageKey, list[ProviderCallRecord]] = defaultdict(list)
    record_list = tuple(records)
    for record in record_list:
        groups[
            _UsageKey(
                operation=record.operation,
                provider=record.provider,
                model=record.model,
            )
        ].append(record)

    operations = tuple(
        _summarize_operation(key, groups[key])
        for key in sorted(
            groups,
            key=lambda item: (item.operation, item.provider, item.model),
        )
    )
    costs = [
        summary.estimated_cost_usd
        for summary in operations
        if summary.estimated_cost_usd is not None
    ]
    return EvalProviderUsageSummary(
        total_call_count=len(record_list),
        total_estimated_cost_usd=round(sum(costs), 12) if costs else None,
        operations=operations,
    )


def _validate_rerank_candidate_limit(
    suite: EvalSuite,
    *,
    reranker: RerankProvider | None,
    rerank_candidate_limit: int | None,
) -> None:
    validate_hosted_rerank_eval_options(
        suite,
        rerank_candidate_limit=rerank_candidate_limit,
    )
    if rerank_candidate_limit is None:
        return
    if reranker is None:
        raise EvalConfigurationError(
            "rerank provider is required when rerank_candidate_limit is set"
        )


@dataclass(frozen=True, slots=True)
class _UsageKey:
    operation: ProviderOperation
    provider: str
    model: str


def _summarize_operation(
    key: _UsageKey,
    records: list[ProviderCallRecord],
) -> EvalProviderUsageOperationSummary:
    costs = [
        record.estimated_cost_usd
        for record in records
        if record.estimated_cost_usd is not None
    ]
    return EvalProviderUsageOperationSummary(
        operation=key.operation,
        provider=key.provider,
        model=key.model,
        call_count=len(records),
        succeeded_count=sum(1 for record in records if record.outcome == "succeeded"),
        failed_count=sum(1 for record in records if record.outcome == "failed"),
        blocked_count=sum(1 for record in records if record.outcome == "blocked"),
        input_tokens=_sum_optional(record.usage.input_tokens for record in records),
        output_tokens=_sum_optional(record.usage.output_tokens for record in records),
        total_tokens=_sum_optional(record.usage.total_tokens for record in records),
        input_count=_sum_optional(record.usage.input_count for record in records),
        estimated_cost_usd=round(sum(costs), 12) if costs else None,
        usage_unavailable_count=sum(
            1 for record in records if record.usage_source == "unavailable"
        ),
    )


def _sum_optional(values: Iterable[int | None]) -> int | None:
    active = [value for value in values if value is not None]
    if not active:
        return None
    return sum(active)
