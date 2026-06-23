"""Modelos internos para datasets y resultados de evals."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from adaptive_rag.provider_usage import ProviderOperation
from adaptive_rag.retrieval import RetrievalMetadataFilter

EvalCaseKind = Literal["retrieval", "chat"]
EvalCaseComparisonOutcome = Literal["improvement", "tie", "regression"]
EvalRunMode = Literal["offline", "hosted"]
EvalRiskFamily = Literal[
    "identifier_exact",
    "metadata_guard",
    "multi_evidence",
    "rerank_regression",
    "semantic_distractor",
]
EvalStatus = Literal["passed", "failed"]


@dataclass(frozen=True, slots=True)
class EvalCaseMetadata:
    """Metadata acotada que explica la intencion de un caso de eval."""

    intent: str | None = None
    difficulty: str | None = None
    risk_family: EvalRiskFamily | None = None
    coverage_notes: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class EvalEvidence:
    """Evidence versionada declarada por una suite offline."""

    id: str
    text: str
    source_type: str
    source_external_id: str
    tags: tuple[str, ...] = ()
    metadata: dict[str, object] | None = None
    embedding: tuple[float, ...] | None = None
    contextual_summary: str | None = None


@dataclass(frozen=True, slots=True)
class EvalThresholds:
    """Umbrales agregados soportados por el baseline inicial."""

    retrieval_hit_rate: float | None = None
    chat_citation_coverage: float | None = None

    def as_metrics(self) -> dict[str, float]:
        values: dict[str, float] = {}
        if self.chat_citation_coverage is not None:
            values["chat_citation_coverage"] = self.chat_citation_coverage
        if self.retrieval_hit_rate is not None:
            values["retrieval_hit_rate"] = self.retrieval_hit_rate
        return values


@dataclass(frozen=True, slots=True)
class RetrievalEvalCase:
    """Caso de eval que ejercita RetrievalService."""

    id: str
    query: str
    expected_evidence_ids: tuple[str, ...]
    limit: int = 10
    metadata_filter: RetrievalMetadataFilter | None = None
    case_metadata: EvalCaseMetadata | None = None


@dataclass(frozen=True, slots=True)
class ChatEvalCase:
    """Caso de eval que ejercita ChatService."""

    id: str
    message: str
    expected_evidence_ids: tuple[str, ...]
    retrieval_limit: int = 5
    metadata_filter: RetrievalMetadataFilter | None = None
    expected_tool_queries: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class EvalSuite:
    """Suite versionada de casos offline."""

    schema_version: int
    suite_id: str
    description: str | None
    thresholds: EvalThresholds
    evidence: tuple[EvalEvidence, ...]
    retrieval_cases: tuple[RetrievalEvalCase, ...]
    chat_cases: tuple[ChatEvalCase, ...]


@dataclass(frozen=True, slots=True)
class EvalObservedCitation:
    """Citation observada por un runner de evals."""

    evidence_id: str
    chunk_id: str
    rank: int
    score: float
    source_external_id: str
    snippet: str


@dataclass(frozen=True, slots=True)
class EvalCaseResult:
    """Resultado serializable de un caso individual."""

    id: str
    kind: EvalCaseKind
    status: EvalStatus
    metrics: dict[str, float]
    errors: tuple[str, ...] = ()
    observed_evidence_ids: tuple[str, ...] = ()
    observed_citations: tuple[EvalObservedCitation, ...] = ()
    observed_tool_queries: tuple[str, ...] = ()
    case_metadata: EvalCaseMetadata | None = None


@dataclass(frozen=True, slots=True)
class EvalCaseComparison:
    """Comparacion por caso entre dense baseline y reranked retrieval."""

    id: str
    outcome: EvalCaseComparisonOutcome
    dense_status: EvalStatus
    reranked_status: EvalStatus
    dense_best_rank: float
    reranked_best_rank: float
    best_rank_delta: float
    dense_observed_evidence_ids: tuple[str, ...] = ()
    reranked_observed_evidence_ids: tuple[str, ...] = ()
    gained_evidence_ids: tuple[str, ...] = ()
    lost_evidence_ids: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class EvalProviderUsageOperationSummary:
    """Usage/costo agregado por provider, modelo y operacion."""

    operation: ProviderOperation
    provider: str
    model: str
    call_count: int
    succeeded_count: int
    failed_count: int
    blocked_count: int
    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None
    input_count: int | None = None
    estimated_cost_usd: float | None = None
    usage_unavailable_count: int = 0


@dataclass(frozen=True, slots=True)
class EvalProviderUsageSummary:
    """Usage/costo agregado para una corrida hosted de evals."""

    total_call_count: int
    total_estimated_cost_usd: float | None
    operations: tuple[EvalProviderUsageOperationSummary, ...]


@dataclass(frozen=True, slots=True)
class EvalRunOptions:
    """Opciones de ejecucion comunes para evals offline y hosted."""

    mode: EvalRunMode = "offline"
    provider: str = "qwen"
    max_cost_usd: float | None = None

    def is_hosted(self) -> bool:
        return self.mode == "hosted"


@dataclass(frozen=True, slots=True)
class EvalRunReport:
    """Reporte agregado de una corrida de evals."""

    suite_id: str
    status: EvalStatus
    metrics: dict[str, float]
    thresholds: dict[str, float]
    cases: tuple[EvalCaseResult, ...]
    mode: EvalRunMode = "offline"
    provider_usage: EvalProviderUsageSummary | None = None
    comparison_metrics: dict[str, float] = field(default_factory=dict)
    comparison_cases: tuple[EvalCaseComparison, ...] = ()
