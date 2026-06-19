"""Modelos internos para datasets y resultados de evals."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from adaptive_rag.retrieval import RetrievalMetadataFilter

EvalCaseKind = Literal["retrieval", "chat"]
EvalStatus = Literal["passed", "failed"]


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


@dataclass(frozen=True, slots=True)
class EvalRunReport:
    """Reporte agregado de una corrida de evals."""

    suite_id: str
    status: EvalStatus
    metrics: dict[str, float]
    thresholds: dict[str, float]
    cases: tuple[EvalCaseResult, ...]
