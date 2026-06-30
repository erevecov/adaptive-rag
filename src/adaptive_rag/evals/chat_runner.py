"""Runner offline de evals de chat."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from adaptive_rag.chat import (
    ChatRequest,
    ChatRunner,
    ChatService,
    ChatServiceError,
    RetrievalGroundedChatRunner,
)
from adaptive_rag.embeddings import (
    DenseEmbeddingProvider,
    FakeDenseEmbeddingProvider,
    FakeSparseEmbeddingProvider,
    SparseEmbeddingPipeline,
    SparseEmbeddingProvider,
)
from adaptive_rag.evals.fixtures import (
    EvalRetrievalFixtureProject,
    build_retrieval_fixture_project,
)
from adaptive_rag.evals.metrics import passes_threshold, ratio
from adaptive_rag.evals.models import (
    ChatEvalCase,
    EvalCaseResult,
    EvalObservedCitation,
    EvalRunReport,
    EvalStatus,
    EvalSuite,
)
from adaptive_rag.retrieval import RetrievalService
from adaptive_rag.retrieval.payloads import RetrievalResultPayload


def run_chat_eval_suite(
    session: Session,
    suite: EvalSuite,
    *,
    provider: DenseEmbeddingProvider | None = None,
    sparse_provider: SparseEmbeddingProvider | None = None,
    runner: ChatRunner | None = None,
) -> EvalRunReport:
    """Ejecuta casos de chat de una suite sin llamar providers hosted."""

    active_provider = provider or FakeDenseEmbeddingProvider()
    active_sparse_provider = sparse_provider or FakeSparseEmbeddingProvider()
    fixture_project = build_retrieval_fixture_project(
        session,
        suite,
        provider=active_provider,
    )
    sparse_pipeline = SparseEmbeddingPipeline(
        session,
        provider=active_sparse_provider,
    )
    for document_version_id in fixture_project.document_version_ids:
        sparse_pipeline.embed_document_version(
            project_id=fixture_project.project_id,
            document_version_id=document_version_id,
        )
    service = ChatService(
        runner=runner or RetrievalGroundedChatRunner(),
        retrieval_service=RetrievalService(
            session,
            provider=active_provider,
            sparse_provider=active_sparse_provider,
        ),
    )
    cases = tuple(
        _run_chat_case(
            service,
            fixture_project=fixture_project,
            chat_case=chat_case,
        )
        for chat_case in suite.chat_cases
    )
    passed_count = sum(1 for case in cases if case.status == "passed")
    matched_count = sum(case.metrics["matched_count"] for case in cases)
    expected_count = sum(case.metrics["expected_count"] for case in cases)
    citation_coverage = ratio(int(matched_count), int(expected_count))
    metrics = {
        "chat_case_count": float(len(cases)),
        "chat_citation_coverage": citation_coverage,
        "chat_passed_count": float(passed_count),
    }
    thresholds = _chat_thresholds(suite)
    status: EvalStatus = (
        "passed"
        if all(case.status == "passed" for case in cases)
        and passes_threshold(
            citation_coverage,
            suite.thresholds.chat_citation_coverage,
        )
        else "failed"
    )
    return EvalRunReport(
        suite_id=suite.suite_id,
        status=status,
        metrics=metrics,
        thresholds=thresholds,
        cases=cases,
    )


def _run_chat_case(
    service: ChatService,
    *,
    fixture_project: EvalRetrievalFixtureProject,
    chat_case: ChatEvalCase,
) -> EvalCaseResult:
    try:
        response = service.respond(
            ChatRequest(
                project_id=fixture_project.project_id,
                message=chat_case.message,
                retrieval_limit=chat_case.retrieval_limit,
                metadata_filter=chat_case.metadata_filter,
            )
        )
    except ChatServiceError as exc:
        return EvalCaseResult(
            id=chat_case.id,
            kind="chat",
            status="failed",
            metrics={
                "citation_coverage": 0.0,
                "cited_count": 0.0,
                "expected_count": float(len(chat_case.expected_evidence_ids)),
                "matched_count": 0.0,
                "tool_call_count": 0.0,
                "tool_query_match": 0.0,
            },
            errors=(f"chat failed: {exc}",),
        )

    observed_evidence_ids = tuple(
        fixture_project.evidence_id_by_chunk_id[UUID(citation["chunk_id"])]
        for citation in response.citations
    )
    observed_tool_queries = tuple(
        tool_call.query
        for tool_call in response.tool_calls
        if tool_call.query is not None
    )
    missing_evidence = tuple(
        evidence_id
        for evidence_id in chat_case.expected_evidence_ids
        if evidence_id not in set(observed_evidence_ids)
    )
    matched_count = len(chat_case.expected_evidence_ids) - len(missing_evidence)
    citation_coverage = ratio(matched_count, len(chat_case.expected_evidence_ids))
    tool_query_match = _tool_query_match(
        observed_tool_queries,
        expected_tool_queries=chat_case.expected_tool_queries,
    )
    errors = _chat_errors(
        missing_evidence,
        observed_tool_queries=observed_tool_queries,
        expected_tool_queries=chat_case.expected_tool_queries,
    )
    return EvalCaseResult(
        id=chat_case.id,
        kind="chat",
        status="passed" if not errors else "failed",
        metrics={
            "citation_coverage": citation_coverage,
            "cited_count": float(len(response.citations)),
            "expected_count": float(len(chat_case.expected_evidence_ids)),
            "matched_count": float(matched_count),
            "tool_call_count": float(len(response.tool_calls)),
            "tool_query_match": tool_query_match,
        },
        errors=errors,
        observed_evidence_ids=observed_evidence_ids,
        observed_citations=tuple(
            _observed_citation(
                citation,
                evidence_id=evidence_id,
                rank=rank,
            )
            for rank, (citation, evidence_id) in enumerate(
                zip(response.citations, observed_evidence_ids, strict=True),
                start=1,
            )
        ),
        observed_tool_queries=observed_tool_queries,
    )


def _observed_citation(
    citation: RetrievalResultPayload,
    *,
    evidence_id: str,
    rank: int,
) -> EvalObservedCitation:
    return EvalObservedCitation(
        evidence_id=evidence_id,
        chunk_id=citation["chunk_id"],
        rank=rank,
        score=citation["score"],
        source_external_id=citation["citation"]["source_external_id"],
        snippet=citation["citation"]["snippet"],
    )


def _chat_errors(
    missing_evidence: tuple[str, ...],
    *,
    observed_tool_queries: tuple[str, ...],
    expected_tool_queries: tuple[str, ...],
) -> tuple[str, ...]:
    errors: list[str] = []
    if missing_evidence:
        errors.append(f"missing expected evidence: {', '.join(missing_evidence)}")
    if expected_tool_queries and observed_tool_queries != expected_tool_queries:
        errors.append(
            "tool query mismatch: expected "
            f"{list(expected_tool_queries)}, got {list(observed_tool_queries)}"
        )
    return tuple(errors)


def _tool_query_match(
    observed_tool_queries: tuple[str, ...],
    *,
    expected_tool_queries: tuple[str, ...],
) -> float:
    if not expected_tool_queries:
        return 1.0
    return 1.0 if observed_tool_queries == expected_tool_queries else 0.0


def _chat_thresholds(suite: EvalSuite) -> dict[str, float]:
    if suite.thresholds.chat_citation_coverage is None:
        return {}
    return {"chat_citation_coverage": suite.thresholds.chat_citation_coverage}
