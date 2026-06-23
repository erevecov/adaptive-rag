"""Runner offline de evals de retrieval."""

from __future__ import annotations

from sqlalchemy.orm import Session

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
    EvalCaseResult,
    EvalObservedCitation,
    EvalRunReport,
    EvalStatus,
    EvalSuite,
    RetrievalEvalCase,
)
from adaptive_rag.graph import GraphRetriever
from adaptive_rag.rerank import RerankProvider
from adaptive_rag.retrieval import (
    RetrievalRerankOptions,
    RetrievalSearchRequest,
    RetrievalSearchResult,
    RetrievalService,
    RetrievalServiceError,
    RetrievalStrategy,
)


def run_retrieval_eval_suite(
    session: Session,
    suite: EvalSuite,
    *,
    provider: DenseEmbeddingProvider | None = None,
    sparse_provider: SparseEmbeddingProvider | None = None,
    reranker: RerankProvider | None = None,
    rerank_options: RetrievalRerankOptions | None = None,
    strategy: RetrievalStrategy = "dense",
    graph_retriever: GraphRetriever | None = None,
    fixture_project: EvalRetrievalFixtureProject | None = None,
) -> EvalRunReport:
    """Ejecuta los casos de retrieval de una suite sin llamar providers hosted."""

    active_provider = provider or FakeDenseEmbeddingProvider()
    active_fixture_project = fixture_project or build_retrieval_fixture_project(
        session,
        suite,
        provider=active_provider,
    )
    if strategy == "dense_sparse":
        active_sparse_provider = sparse_provider or FakeSparseEmbeddingProvider()
        sparse_pipeline = SparseEmbeddingPipeline(
            session,
            provider=active_sparse_provider,
        )
        for document_version_id in active_fixture_project.document_version_ids:
            sparse_pipeline.embed_document_version(
                project_id=active_fixture_project.project_id,
                document_version_id=document_version_id,
            )
    service = RetrievalService(
        session,
        provider=active_provider,
        sparse_provider=(
            (sparse_provider or FakeSparseEmbeddingProvider())
            if strategy == "dense_sparse"
            else None
        ),
        reranker=reranker,
        graph_retriever=graph_retriever,
    )
    cases = tuple(
        _run_retrieval_case(
            service,
            fixture_project=active_fixture_project,
            retrieval_case=retrieval_case,
            rerank_options=rerank_options,
            strategy=strategy,
        )
        for retrieval_case in suite.retrieval_cases
    )
    passed_count = sum(1 for case in cases if case.status == "passed")
    hit_rate = ratio(passed_count, len(cases))
    metrics = {
        "retrieval_case_count": float(len(cases)),
        "retrieval_hit_rate": hit_rate,
        "retrieval_passed_count": float(passed_count),
    }
    thresholds = _retrieval_thresholds(suite)
    status: EvalStatus = (
        "passed"
        if all(case.status == "passed" for case in cases)
        and passes_threshold(hit_rate, suite.thresholds.retrieval_hit_rate)
        else "failed"
    )
    return EvalRunReport(
        suite_id=suite.suite_id,
        status=status,
        metrics=metrics,
        thresholds=thresholds,
        cases=cases,
    )


def _run_retrieval_case(
    service: RetrievalService,
    *,
    fixture_project: EvalRetrievalFixtureProject,
    retrieval_case: RetrievalEvalCase,
    rerank_options: RetrievalRerankOptions | None,
    strategy: RetrievalStrategy,
) -> EvalCaseResult:
    try:
        results = service.search(
            RetrievalSearchRequest(
                project_id=fixture_project.project_id,
                query=retrieval_case.query,
                limit=retrieval_case.limit,
                metadata_filter=retrieval_case.metadata_filter,
                rerank=rerank_options,
                strategy=strategy,
            )
        )
    except RetrievalServiceError as exc:
        return EvalCaseResult(
            id=retrieval_case.id,
            kind="retrieval",
            status="failed",
            metrics={
                "best_rank": 0.0,
                "expected_count": float(len(retrieval_case.expected_evidence_ids)),
                "hit": 0.0,
                "matched_count": 0.0,
                "missing_count": float(len(retrieval_case.expected_evidence_ids)),
                "retrieved_count": 0.0,
            },
            case_metadata=retrieval_case.case_metadata,
            errors=(f"retrieval failed: {exc}",),
        )

    observed_evidence_ids = tuple(
        fixture_project.evidence_id_by_chunk_id[result.chunk_id] for result in results
    )
    observed_citations = tuple(
        _observed_citation(
            result,
            evidence_id=evidence_id,
            rank=rank,
        )
        for rank, (result, evidence_id) in enumerate(
            zip(results, observed_evidence_ids, strict=True),
            start=1,
        )
    )
    missing = tuple(
        evidence_id
        for evidence_id in retrieval_case.expected_evidence_ids
        if evidence_id not in set(observed_evidence_ids)
    )
    matched_count = len(retrieval_case.expected_evidence_ids) - len(missing)
    best_rank = _best_rank(
        observed_evidence_ids,
        expected_evidence_ids=retrieval_case.expected_evidence_ids,
    )
    return EvalCaseResult(
        id=retrieval_case.id,
        kind="retrieval",
        status="passed" if not missing else "failed",
        metrics={
            "best_rank": float(best_rank),
            "expected_count": float(len(retrieval_case.expected_evidence_ids)),
            "hit": 1.0 if not missing else 0.0,
            "matched_count": float(matched_count),
            "missing_count": float(len(missing)),
            "retrieved_count": float(len(results)),
        },
        case_metadata=retrieval_case.case_metadata,
        errors=_missing_errors(missing),
        observed_evidence_ids=observed_evidence_ids,
        observed_citations=observed_citations,
    )


def _observed_citation(
    result: RetrievalSearchResult,
    *,
    evidence_id: str,
    rank: int,
) -> EvalObservedCitation:
    return EvalObservedCitation(
        evidence_id=evidence_id,
        chunk_id=str(result.chunk_id),
        rank=rank,
        score=result.score,
        source_external_id=result.citation.source_external_id,
        snippet=result.citation.snippet,
    )


def _best_rank(
    observed_evidence_ids: tuple[str, ...],
    *,
    expected_evidence_ids: tuple[str, ...],
) -> int:
    expected = set(expected_evidence_ids)
    ranks = [
        rank
        for rank, evidence_id in enumerate(observed_evidence_ids, start=1)
        if evidence_id in expected
    ]
    return min(ranks) if ranks else 0


def _missing_errors(missing: tuple[str, ...]) -> tuple[str, ...]:
    if not missing:
        return ()
    return (f"missing expected evidence: {', '.join(missing)}",)


def _retrieval_thresholds(suite: EvalSuite) -> dict[str, float]:
    if suite.thresholds.retrieval_hit_rate is None:
        return {}
    return {"retrieval_hit_rate": suite.thresholds.retrieval_hit_rate}
