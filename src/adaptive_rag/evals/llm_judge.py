"""Opt-in LLM-as-judge metrics for chat eval cases (Bloque C)."""

from __future__ import annotations

import json
import re
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass, replace
from typing import Protocol

from adaptive_rag.evals.errors import EvalConfigurationError
from adaptive_rag.evals.models import EvalCaseResult, EvalRunReport
from adaptive_rag.provider_usage import (
    InMemoryProviderUsageTracker,
    ProviderBudgetExceededError,
    ProviderBudgetGuard,
    ProviderCallOutcome,
    ProviderCallRecord,
    ProviderTokenUsage,
)

_JSON_OBJECT_RE = re.compile(r"\{[^{}]*\}", re.DOTALL)


@dataclass(frozen=True, slots=True)
class JudgeScores:
    faithfulness: float
    response_relevancy: float


class LlmJudge(Protocol):
    def score(
        self,
        *,
        question: str,
        answer: str,
        contexts: Sequence[str],
        citation_coverage: float,
    ) -> JudgeScores:
        """Return scores in [0, 1]."""


def validate_llm_judge_options(
    *,
    enabled: bool,
    max_cost_usd: float | None,
) -> None:
    """Fail closed when judge is enabled without a positive budget."""

    if not enabled:
        return
    if max_cost_usd is None or max_cost_usd <= 0:
        raise EvalConfigurationError(
            "LLM-as-judge requires --max-cost-usd greater than 0"
        )


class FakeDeterministicJudge:
    """Offline-safe judge: faithfulness mirrors citation coverage."""

    def score(
        self,
        *,
        question: str,
        answer: str,
        contexts: Sequence[str],
        citation_coverage: float,
    ) -> JudgeScores:
        del question, contexts
        faithfulness = max(0.0, min(1.0, float(citation_coverage)))
        relevancy = 1.0 if answer.strip() else 0.0
        return JudgeScores(
            faithfulness=faithfulness,
            response_relevancy=relevancy,
        )


class PromptLlmJudge:
    """Live-ish judge that asks a text completer for JSON scores."""

    def __init__(
        self,
        *,
        complete: Callable[[str], str],
        usage_tracker: InMemoryProviderUsageTracker | None = None,
        budget_guard: ProviderBudgetGuard | None = None,
        provider: str = "qwen",
        model: str = "eval-judge",
        estimated_cost_usd: float = 0.0,
    ) -> None:
        self._complete = complete
        self._usage_tracker = usage_tracker
        self._budget_guard = budget_guard or ProviderBudgetGuard()
        self._provider = provider
        self._model = model
        self._estimated_cost_usd = estimated_cost_usd

    def score(
        self,
        *,
        question: str,
        answer: str,
        contexts: Sequence[str],
        citation_coverage: float,
    ) -> JudgeScores:
        del citation_coverage
        prompt = _build_judge_prompt(
            question=question,
            answer=answer,
            contexts=contexts,
        )
        started = time.perf_counter()
        try:
            raw = self._complete(prompt)
        except Exception as exc:
            self._record(
                outcome="failed",
                duration_ms=_elapsed_ms(started),
                error_type=type(exc).__name__,
            )
            raise
        duration_ms = _elapsed_ms(started)
        record = self._make_record(outcome="succeeded", duration_ms=duration_ms)
        try:
            self._budget_guard.enforce(record)
        except ProviderBudgetExceededError:
            blocked = replace(record, outcome="blocked")
            if self._usage_tracker is not None:
                self._usage_tracker.record(blocked)
            raise
        if self._usage_tracker is not None:
            self._usage_tracker.record(record)
        return _parse_judge_json(raw)

    def _record(
        self,
        *,
        outcome: ProviderCallOutcome,
        duration_ms: int,
        error_type: str | None = None,
    ) -> None:
        if self._usage_tracker is None:
            return
        self._usage_tracker.record(
            self._make_record(
                outcome=outcome,
                duration_ms=duration_ms,
                error_type=error_type,
            )
        )

    def _make_record(
        self,
        *,
        outcome: ProviderCallOutcome,
        duration_ms: int,
        error_type: str | None = None,
    ) -> ProviderCallRecord:
        return ProviderCallRecord(
            provider=self._provider,
            model=self._model,
            operation="eval_judge",
            outcome=outcome,
            duration_ms=duration_ms,
            usage=ProviderTokenUsage(),
            usage_source="unavailable",
            estimated_cost_usd=self._estimated_cost_usd,
            error_type=error_type,
        )


def apply_llm_judge(
    report: EvalRunReport,
    *,
    judge: LlmJudge,
    questions_by_case_id: dict[str, str] | None = None,
) -> EvalRunReport:
    """Attach judge metrics to chat cases; leave suite status unchanged."""

    questions = questions_by_case_id or {}
    judged_cases: list[EvalCaseResult] = []
    faithfulness_values: list[float] = []
    relevancy_values: list[float] = []

    for case in report.cases:
        if case.kind != "chat" or case.answer is None:
            judged_cases.append(case)
            continue
        scores = judge.score(
            question=questions.get(case.id, case.id),
            answer=case.answer,
            contexts=case.context_snippets,
            citation_coverage=float(case.metrics.get("citation_coverage", 0.0)),
        )
        faithfulness_values.append(scores.faithfulness)
        relevancy_values.append(scores.response_relevancy)
        judged_cases.append(
            replace(
                case,
                metrics={
                    **case.metrics,
                    "judge_faithfulness": scores.faithfulness,
                    "judge_response_relevancy": scores.response_relevancy,
                },
            )
        )

    if not faithfulness_values:
        return replace(
            report,
            cases=tuple(judged_cases),
            metrics={
                **report.metrics,
                "judge_case_count": 0.0,
            },
        )

    mean_f = sum(faithfulness_values) / len(faithfulness_values)
    mean_r = sum(relevancy_values) / len(relevancy_values)
    return replace(
        report,
        cases=tuple(judged_cases),
        metrics={
            **report.metrics,
            "judge_case_count": float(len(faithfulness_values)),
            "judge_faithfulness_mean": mean_f,
            "judge_response_relevancy_mean": mean_r,
        },
    )


def _build_judge_prompt(
    *,
    question: str,
    answer: str,
    contexts: Sequence[str],
) -> str:
    context_block = "\n".join(f"- {item}" for item in contexts) or "- (none)"
    return (
        "You are an evaluation judge. Score the answer using only the contexts.\n"
        "Return a single JSON object with keys faithfulness and "
        "response_relevancy as numbers between 0 and 1.\n"
        f"Question: {question}\n"
        f"Answer: {answer}\n"
        f"Contexts:\n{context_block}\n"
        "JSON:"
    )


def _parse_judge_json(raw: str) -> JudgeScores:
    text = raw.strip()
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        match = _JSON_OBJECT_RE.search(text)
        if match is None:
            raise EvalConfigurationError("LLM judge returned non-JSON scores") from None
        payload = json.loads(match.group(0))
    if not isinstance(payload, dict):
        raise EvalConfigurationError("LLM judge JSON must be an object")
    try:
        faithfulness = float(payload["faithfulness"])
        relevancy = float(payload["response_relevancy"])
    except (KeyError, TypeError, ValueError) as exc:
        raise EvalConfigurationError(
            "LLM judge JSON must include faithfulness and response_relevancy"
        ) from exc
    return JudgeScores(
        faithfulness=_clamp01(faithfulness),
        response_relevancy=_clamp01(relevancy),
    )


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def _elapsed_ms(started: float) -> int:
    return max(0, int((time.perf_counter() - started) * 1000))
