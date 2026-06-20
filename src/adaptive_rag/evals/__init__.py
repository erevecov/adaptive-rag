"""Contrato de datasets y reportes para evals offline."""

from adaptive_rag.evals.candidate_limit_matrix import (
    CandidateLimitEvalMatrix,
    CandidateLimitEvalMatrixRow,
    build_candidate_limit_eval_matrix,
    serialize_candidate_limit_eval_matrix,
)
from adaptive_rag.evals.candidate_limit_runner import (
    CandidateLimitABRunReport,
    CandidateLimitABRunRow,
    run_candidate_limit_ab_retrieval_eval_suite,
    serialize_candidate_limit_ab_run_report,
)
from adaptive_rag.evals.chat_runner import run_chat_eval_suite
from adaptive_rag.evals.datasets import load_eval_suite
from adaptive_rag.evals.errors import EvalConfigurationError, EvalDatasetError
from adaptive_rag.evals.hosted import (
    run_hosted_chat_eval_suite,
    run_hosted_eval_suite,
    run_hosted_retrieval_eval_suite,
    summarize_provider_usage,
    validate_hosted_eval_credentials,
    validate_hosted_eval_options,
    validate_hosted_rerank_eval_options,
)
from adaptive_rag.evals.models import (
    ChatEvalCase,
    EvalCaseComparison,
    EvalCaseComparisonOutcome,
    EvalCaseMetadata,
    EvalCaseResult,
    EvalEvidence,
    EvalObservedCitation,
    EvalProviderUsageOperationSummary,
    EvalProviderUsageSummary,
    EvalRiskFamily,
    EvalRunMode,
    EvalRunOptions,
    EvalRunReport,
    EvalSuite,
    EvalThresholds,
    RetrievalEvalCase,
)
from adaptive_rag.evals.reports import serialize_eval_report
from adaptive_rag.evals.retrieval_runner import run_retrieval_eval_suite
from adaptive_rag.evals.runner import run_eval_suite

__all__ = [
    "CandidateLimitEvalMatrix",
    "CandidateLimitEvalMatrixRow",
    "CandidateLimitABRunReport",
    "CandidateLimitABRunRow",
    "ChatEvalCase",
    "EvalCaseComparison",
    "EvalCaseComparisonOutcome",
    "EvalCaseMetadata",
    "EvalCaseResult",
    "EvalConfigurationError",
    "EvalDatasetError",
    "EvalEvidence",
    "EvalObservedCitation",
    "EvalProviderUsageOperationSummary",
    "EvalProviderUsageSummary",
    "EvalRiskFamily",
    "EvalRunMode",
    "EvalRunOptions",
    "EvalRunReport",
    "EvalSuite",
    "EvalThresholds",
    "RetrievalEvalCase",
    "build_candidate_limit_eval_matrix",
    "load_eval_suite",
    "run_chat_eval_suite",
    "run_candidate_limit_ab_retrieval_eval_suite",
    "run_eval_suite",
    "run_hosted_eval_suite",
    "run_hosted_chat_eval_suite",
    "run_hosted_retrieval_eval_suite",
    "run_retrieval_eval_suite",
    "serialize_eval_report",
    "serialize_candidate_limit_ab_run_report",
    "serialize_candidate_limit_eval_matrix",
    "summarize_provider_usage",
    "validate_hosted_eval_credentials",
    "validate_hosted_eval_options",
    "validate_hosted_rerank_eval_options",
]
