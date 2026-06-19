"""Contrato de datasets y reportes para evals offline."""

from adaptive_rag.evals.chat_runner import run_chat_eval_suite
from adaptive_rag.evals.datasets import load_eval_suite
from adaptive_rag.evals.errors import EvalDatasetError
from adaptive_rag.evals.models import (
    ChatEvalCase,
    EvalCaseResult,
    EvalEvidence,
    EvalObservedCitation,
    EvalRunReport,
    EvalSuite,
    EvalThresholds,
    RetrievalEvalCase,
)
from adaptive_rag.evals.reports import serialize_eval_report
from adaptive_rag.evals.retrieval_runner import run_retrieval_eval_suite

__all__ = [
    "ChatEvalCase",
    "EvalCaseResult",
    "EvalDatasetError",
    "EvalEvidence",
    "EvalObservedCitation",
    "EvalRunReport",
    "EvalSuite",
    "EvalThresholds",
    "RetrievalEvalCase",
    "load_eval_suite",
    "run_chat_eval_suite",
    "run_retrieval_eval_suite",
    "serialize_eval_report",
]
