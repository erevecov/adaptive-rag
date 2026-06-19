"""Runner agregado para suites de evals offline."""

from __future__ import annotations

from sqlalchemy.orm import Session

from adaptive_rag.chat import ChatRunner
from adaptive_rag.embeddings import DenseEmbeddingProvider
from adaptive_rag.evals.chat_runner import run_chat_eval_suite
from adaptive_rag.evals.models import EvalRunReport, EvalStatus, EvalSuite
from adaptive_rag.evals.retrieval_runner import run_retrieval_eval_suite


def run_eval_suite(
    session: Session,
    suite: EvalSuite,
    *,
    provider: DenseEmbeddingProvider | None = None,
    chat_runner: ChatRunner | None = None,
) -> EvalRunReport:
    """Ejecuta retrieval y chat de una suite en un reporte unico."""

    retrieval_report = run_retrieval_eval_suite(
        session,
        suite,
        provider=provider,
    )
    chat_report = run_chat_eval_suite(
        session,
        suite,
        provider=provider,
        runner=chat_runner,
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
    )
