"""Contrato de datasets y reportes para evals offline."""

from adaptive_rag.evals.datasets import load_eval_suite
from adaptive_rag.evals.errors import EvalDatasetError
from adaptive_rag.evals.models import (
    ChatEvalCase,
    EvalCaseResult,
    EvalEvidence,
    EvalRunReport,
    EvalSuite,
    EvalThresholds,
    RetrievalEvalCase,
)
from adaptive_rag.evals.reports import serialize_eval_report

__all__ = [
    "ChatEvalCase",
    "EvalCaseResult",
    "EvalDatasetError",
    "EvalEvidence",
    "EvalRunReport",
    "EvalSuite",
    "EvalThresholds",
    "RetrievalEvalCase",
    "load_eval_suite",
    "serialize_eval_report",
]
