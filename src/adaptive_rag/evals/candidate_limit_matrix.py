"""Matrix de parametros para comparar candidate limits de rerank."""

from __future__ import annotations

from dataclasses import dataclass

from adaptive_rag.evals.errors import EvalConfigurationError
from adaptive_rag.evals.models import EvalSuite, RetrievalEvalCase


@dataclass(frozen=True, slots=True)
class CandidateLimitEvalMatrixRow:
    """Fila serializable para un candidate limit evaluable."""

    candidate_limit: int
    case_count: int
    case_ids_by_intent: dict[str, tuple[str, ...]]
    case_ids_by_difficulty: dict[str, tuple[str, ...]]
    case_ids_by_risk_family: dict[str, tuple[str, ...]]


@dataclass(frozen=True, slots=True)
class CandidateLimitEvalMatrix:
    """Plan acotado para ejecutar candidate limits sobre una suite."""

    suite_id: str
    case_count: int
    max_case_limit: int
    intent_counts: dict[str, int]
    difficulty_counts: dict[str, int]
    risk_family_counts: dict[str, int]
    rows: tuple[CandidateLimitEvalMatrixRow, ...]


def build_candidate_limit_eval_matrix(
    suite: EvalSuite,
    *,
    candidate_limits: tuple[int, ...],
) -> CandidateLimitEvalMatrix:
    """Construye la parametrizacion de candidate limits para una suite."""

    active_limits = _validate_candidate_limits(suite, candidate_limits)
    cases = suite.retrieval_cases
    case_ids_by_intent = _case_ids_by_metadata(
        cases,
        field="intent",
        fallback="unclassified",
    )
    case_ids_by_difficulty = _case_ids_by_metadata(
        cases,
        field="difficulty",
        fallback="unknown",
    )
    case_ids_by_risk_family = _case_ids_by_metadata(
        cases,
        field="risk_family",
        fallback="uncategorized",
    )
    rows = tuple(
        CandidateLimitEvalMatrixRow(
            candidate_limit=limit,
            case_count=len(cases),
            case_ids_by_intent=case_ids_by_intent,
            case_ids_by_difficulty=case_ids_by_difficulty,
            case_ids_by_risk_family=case_ids_by_risk_family,
        )
        for limit in active_limits
    )
    return CandidateLimitEvalMatrix(
        suite_id=suite.suite_id,
        case_count=len(cases),
        max_case_limit=_max_case_limit(suite),
        intent_counts=_counts(case_ids_by_intent),
        difficulty_counts=_counts(case_ids_by_difficulty),
        risk_family_counts=_counts(case_ids_by_risk_family),
        rows=rows,
    )


def serialize_candidate_limit_eval_matrix(
    matrix: CandidateLimitEvalMatrix,
) -> dict[str, object]:
    """Serializa la matrix con orden estable para reportes y PR bodies."""

    return {
        "suite_id": matrix.suite_id,
        "case_count": matrix.case_count,
        "max_case_limit": matrix.max_case_limit,
        "intent_counts": dict(sorted(matrix.intent_counts.items())),
        "difficulty_counts": dict(sorted(matrix.difficulty_counts.items())),
        "risk_family_counts": dict(sorted(matrix.risk_family_counts.items())),
        "rows": [_serialize_row(row) for row in matrix.rows],
    }


def _validate_candidate_limits(
    suite: EvalSuite,
    candidate_limits: tuple[int, ...],
) -> tuple[int, ...]:
    if len(set(candidate_limits)) != len(candidate_limits):
        raise EvalConfigurationError("candidate_limit values must be unique")
    if any(limit <= 0 for limit in candidate_limits):
        raise EvalConfigurationError("candidate_limit must be positive")
    max_case_limit = _max_case_limit(suite)
    if any(limit < max_case_limit for limit in candidate_limits):
        raise EvalConfigurationError(
            "candidate_limit must be greater than or equal to every "
            "retrieval case limit"
        )
    return tuple(sorted(candidate_limits))


def _max_case_limit(suite: EvalSuite) -> int:
    return max((case.limit for case in suite.retrieval_cases), default=0)


def _case_ids_by_metadata(
    cases: tuple[RetrievalEvalCase, ...],
    *,
    field: str,
    fallback: str,
) -> dict[str, tuple[str, ...]]:
    groups: dict[str, list[str]] = {}
    for case in cases:
        metadata = case.case_metadata
        value = getattr(metadata, field) if metadata is not None else None
        key = value or fallback
        groups.setdefault(key, []).append(case.id)
    return {key: tuple(value) for key, value in sorted(groups.items())}


def _counts(groups: dict[str, tuple[str, ...]]) -> dict[str, int]:
    return {key: len(value) for key, value in sorted(groups.items())}


def _serialize_row(row: CandidateLimitEvalMatrixRow) -> dict[str, object]:
    return {
        "candidate_limit": row.candidate_limit,
        "case_count": row.case_count,
        "case_ids_by_intent": _serialize_groups(row.case_ids_by_intent),
        "case_ids_by_difficulty": _serialize_groups(row.case_ids_by_difficulty),
        "case_ids_by_risk_family": _serialize_groups(
            row.case_ids_by_risk_family
        ),
    }


def _serialize_groups(groups: dict[str, tuple[str, ...]]) -> dict[str, list[str]]:
    return {key: list(value) for key, value in sorted(groups.items())}

