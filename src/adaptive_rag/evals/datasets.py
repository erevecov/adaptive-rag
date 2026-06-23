"""Carga y validacion estricta de fixtures de evals."""

from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path

from adaptive_rag.evals.errors import EvalDatasetError
from adaptive_rag.evals.models import (
    ChatEvalCase,
    EvalCaseMetadata,
    EvalEvidence,
    EvalRiskFamily,
    EvalSuite,
    EvalThresholds,
    RetrievalEvalCase,
)
from adaptive_rag.evals.validation import (
    expect_int,
    expect_list,
    expect_mapping,
    expect_nonempty_str,
    optional_float,
    optional_nonempty_str,
    optional_positive_int,
    parse_float_tuple,
    parse_required_str_tuple,
    parse_str_tuple,
    reject_unknown_fields,
    required,
)
from adaptive_rag.retrieval import RetrievalMetadataFilter

_RISK_FAMILIES: tuple[EvalRiskFamily, ...] = (
    "identifier_exact",
    "metadata_guard",
    "multi_evidence",
    "rerank_regression",
    "semantic_distractor",
)

_SUITE_FIELDS = frozenset(
    {
        "schema_version",
        "suite_id",
        "description",
        "thresholds",
        "evidence",
        "retrieval_cases",
        "chat_cases",
    }
)
_EVIDENCE_FIELDS = frozenset(
    {
        "contextual_summary",
        "id",
        "text",
        "source_type",
        "source_external_id",
        "tags",
        "metadata",
        "embedding",
    }
)
_RETRIEVAL_CASE_FIELDS = frozenset(
    {
        "id",
        "query",
        "limit",
        "case_metadata",
        "metadata_filter",
        "expected_evidence_ids",
    }
)
_CHAT_CASE_FIELDS = frozenset(
    {
        "id",
        "message",
        "retrieval_limit",
        "metadata_filter",
        "expected_evidence_ids",
        "expected_tool_queries",
    }
)
_FILTER_FIELDS = frozenset({"source_type", "tags"})
_CASE_METADATA_FIELDS = frozenset(
    {"intent", "difficulty", "risk_family", "coverage_notes"}
)
_THRESHOLD_FIELDS = frozenset(
    {"retrieval_hit_rate", "chat_citation_coverage"}
)


def load_eval_suite(path: str | Path) -> EvalSuite:
    """Carga una suite JSON local y valida su contrato antes de ejecutar servicios."""

    suite_path = Path(path)
    try:
        raw = json.loads(suite_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise EvalDatasetError(
            f"{suite_path} is not valid JSON: {exc.msg}"
        ) from exc
    except OSError as exc:
        raise EvalDatasetError(f"could not read eval suite {suite_path}") from exc

    payload = expect_mapping(raw, field_name="suite")
    reject_unknown_fields(payload, allowed=_SUITE_FIELDS, field_name="suite")
    schema_version = expect_int(
        required(payload, "schema_version", field_name="suite"),
        field_name="schema_version",
    )
    if schema_version != 1:
        raise EvalDatasetError(
            f"schema_version must be 1, got {schema_version}"
        )

    evidence = tuple(
        _parse_evidence(item, index=index)
        for index, item in enumerate(
            expect_list(
                required(payload, "evidence", field_name="suite"),
                field_name="evidence",
            )
        )
    )
    evidence_ids = _validate_unique_ids(
        [item.id for item in evidence],
        field_name="evidence",
    )
    retrieval_cases = tuple(
        _parse_retrieval_case(item, index=index)
        for index, item in enumerate(
            expect_list(
                required(payload, "retrieval_cases", field_name="suite"),
                field_name="retrieval_cases",
            )
        )
    )
    chat_cases = tuple(
        _parse_chat_case(item, index=index)
        for index, item in enumerate(
            expect_list(
                required(payload, "chat_cases", field_name="suite"),
                field_name="chat_cases",
            )
        )
    )
    _validate_unique_ids(
        [item.id for item in retrieval_cases],
        field_name="retrieval_cases",
    )
    _validate_unique_ids(
        [item.id for item in chat_cases],
        field_name="chat_cases",
    )
    for retrieval_case in retrieval_cases:
        _validate_expected_evidence(
            retrieval_case.id,
            retrieval_case.expected_evidence_ids,
            evidence_ids,
        )
    for chat_case in chat_cases:
        _validate_expected_evidence(
            chat_case.id,
            chat_case.expected_evidence_ids,
            evidence_ids,
        )

    return EvalSuite(
        schema_version=schema_version,
        suite_id=expect_nonempty_str(
            required(payload, "suite_id", field_name="suite"),
            field_name="suite_id",
        ),
        description=optional_nonempty_str(
            payload.get("description"),
            field_name="description",
        ),
        thresholds=_parse_thresholds(
            required(payload, "thresholds", field_name="suite")
        ),
        evidence=evidence,
        retrieval_cases=retrieval_cases,
        chat_cases=chat_cases,
    )


def _parse_evidence(value: object, *, index: int) -> EvalEvidence:
    field_name = f"evidence[{index}]"
    payload = expect_mapping(value, field_name=field_name)
    reject_unknown_fields(payload, allowed=_EVIDENCE_FIELDS, field_name=field_name)
    return EvalEvidence(
        id=expect_nonempty_str(
            required(payload, "id", field_name=field_name),
            field_name=f"{field_name}.id",
        ),
        text=expect_nonempty_str(
            required(payload, "text", field_name=field_name),
            field_name=f"{field_name}.text",
        ),
        source_type=expect_nonempty_str(
            required(payload, "source_type", field_name=field_name),
            field_name=f"{field_name}.source_type",
        ),
        source_external_id=expect_nonempty_str(
            required(payload, "source_external_id", field_name=field_name),
            field_name=f"{field_name}.source_external_id",
        ),
        tags=parse_str_tuple(payload.get("tags", []), field_name=f"{field_name}.tags"),
        metadata=_parse_metadata(payload.get("metadata"), field_name=field_name),
        embedding=parse_float_tuple(
            payload.get("embedding"),
            field_name=f"{field_name}.embedding",
        ),
        contextual_summary=optional_nonempty_str(
            payload.get("contextual_summary"),
            field_name=f"{field_name}.contextual_summary",
        ),
    )


def _parse_retrieval_case(value: object, *, index: int) -> RetrievalEvalCase:
    field_name = f"retrieval_cases[{index}]"
    payload = expect_mapping(value, field_name=field_name)
    reject_unknown_fields(
        payload,
        allowed=_RETRIEVAL_CASE_FIELDS,
        field_name=field_name,
    )
    return RetrievalEvalCase(
        id=expect_nonempty_str(
            required(payload, "id", field_name=field_name),
            field_name=f"{field_name}.id",
        ),
        query=expect_nonempty_str(
            required(payload, "query", field_name=field_name),
            field_name=f"{field_name}.query",
        ),
        limit=optional_positive_int(
            payload.get("limit"),
            default=10,
            field_name=f"{field_name}.limit",
        ),
        metadata_filter=_parse_metadata_filter(
            payload.get("metadata_filter"),
            field_name=f"{field_name}.metadata_filter",
        ),
        case_metadata=_parse_case_metadata(
            payload.get("case_metadata"),
            field_name=f"{field_name}.case_metadata",
        ),
        expected_evidence_ids=parse_required_str_tuple(
            required(payload, "expected_evidence_ids", field_name=field_name),
            field_name=f"{field_name}.expected_evidence_ids",
        ),
    )


def _parse_chat_case(value: object, *, index: int) -> ChatEvalCase:
    field_name = f"chat_cases[{index}]"
    payload = expect_mapping(value, field_name=field_name)
    reject_unknown_fields(payload, allowed=_CHAT_CASE_FIELDS, field_name=field_name)
    return ChatEvalCase(
        id=expect_nonempty_str(
            required(payload, "id", field_name=field_name),
            field_name=f"{field_name}.id",
        ),
        message=expect_nonempty_str(
            required(payload, "message", field_name=field_name),
            field_name=f"{field_name}.message",
        ),
        retrieval_limit=optional_positive_int(
            payload.get("retrieval_limit"),
            default=5,
            field_name=f"{field_name}.retrieval_limit",
        ),
        metadata_filter=_parse_metadata_filter(
            payload.get("metadata_filter"),
            field_name=f"{field_name}.metadata_filter",
        ),
        expected_evidence_ids=parse_required_str_tuple(
            required(payload, "expected_evidence_ids", field_name=field_name),
            field_name=f"{field_name}.expected_evidence_ids",
        ),
        expected_tool_queries=parse_str_tuple(
            payload.get("expected_tool_queries", []),
            field_name=f"{field_name}.expected_tool_queries",
        ),
    )


def _parse_thresholds(value: object) -> EvalThresholds:
    payload = expect_mapping(value, field_name="thresholds")
    reject_unknown_fields(
        payload,
        allowed=_THRESHOLD_FIELDS,
        field_name="thresholds",
    )
    return EvalThresholds(
        retrieval_hit_rate=optional_float(
            payload.get("retrieval_hit_rate"),
            field_name="thresholds.retrieval_hit_rate",
        ),
        chat_citation_coverage=optional_float(
            payload.get("chat_citation_coverage"),
            field_name="thresholds.chat_citation_coverage",
        ),
    )


def _parse_metadata_filter(
    value: object,
    *,
    field_name: str,
) -> RetrievalMetadataFilter | None:
    if value is None:
        return None
    payload = expect_mapping(value, field_name=field_name)
    reject_unknown_fields(payload, allowed=_FILTER_FIELDS, field_name=field_name)
    return RetrievalMetadataFilter(
        source_type=optional_nonempty_str(
            payload.get("source_type"),
            field_name=f"{field_name}.source_type",
        ),
        tags=parse_str_tuple(
            payload.get("tags", []),
            field_name=f"{field_name}.tags",
        ),
    )


def _parse_case_metadata(
    value: object,
    *,
    field_name: str,
) -> EvalCaseMetadata | None:
    if value is None:
        return None
    payload = expect_mapping(value, field_name=field_name)
    reject_unknown_fields(
        payload,
        allowed=_CASE_METADATA_FIELDS,
        field_name=field_name,
    )
    return EvalCaseMetadata(
        intent=optional_nonempty_str(
            payload.get("intent"),
            field_name=f"{field_name}.intent",
        ),
        difficulty=optional_nonempty_str(
            payload.get("difficulty"),
            field_name=f"{field_name}.difficulty",
        ),
        risk_family=_parse_risk_family(
            payload.get("risk_family"),
            field_name=f"{field_name}.risk_family",
        ),
        coverage_notes=parse_str_tuple(
            payload.get("coverage_notes", []),
            field_name=f"{field_name}.coverage_notes",
        ),
    )


def _parse_risk_family(
    value: object,
    *,
    field_name: str,
) -> EvalRiskFamily | None:
    risk_family = optional_nonempty_str(value, field_name=field_name)
    if risk_family is None:
        return None
    if risk_family not in _RISK_FAMILIES:
        raise EvalDatasetError(
            f"{field_name} must be one of: {', '.join(_RISK_FAMILIES)}"
        )
    return risk_family


def _parse_metadata(value: object, *, field_name: str) -> dict[str, object] | None:
    if value is None:
        return None
    metadata = expect_mapping(value, field_name=f"{field_name}.metadata")
    return dict(metadata)


def _validate_expected_evidence(
    case_id: str,
    expected_evidence_ids: tuple[str, ...],
    evidence_ids: set[str],
) -> None:
    unknown = [
        evidence_id
        for evidence_id in expected_evidence_ids
        if evidence_id not in evidence_ids
    ]
    if unknown:
        raise EvalDatasetError(
            f"{case_id} references unknown evidence: {', '.join(unknown)}"
        )


def _validate_unique_ids(values: Sequence[str], *, field_name: str) -> set[str]:
    seen: set[str] = set()
    for value in values:
        if value in seen:
            raise EvalDatasetError(f"{field_name} has duplicate id: {value}")
        seen.add(value)
    return seen
