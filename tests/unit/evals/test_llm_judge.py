"""Bloque C: opt-in LLM-as-judge with budget gate."""

from __future__ import annotations

import pytest

from adaptive_rag.evals.errors import EvalConfigurationError
from adaptive_rag.evals.llm_judge import (
    FakeDeterministicJudge,
    JudgeScores,
    PromptLlmJudge,
    apply_llm_judge,
    validate_llm_judge_options,
)
from adaptive_rag.evals.models import EvalCaseResult, EvalRunReport
from adaptive_rag.provider_usage import (
    InMemoryProviderUsageTracker,
    ProviderBudgetExceededError,
    ProviderBudgetGuard,
)


def test_validate_requires_positive_budget() -> None:
    with pytest.raises(EvalConfigurationError, match="max-cost-usd"):
        validate_llm_judge_options(enabled=True, max_cost_usd=None)
    with pytest.raises(EvalConfigurationError, match="max-cost-usd"):
        validate_llm_judge_options(enabled=True, max_cost_usd=0)
    validate_llm_judge_options(enabled=True, max_cost_usd=0.5)
    validate_llm_judge_options(enabled=False, max_cost_usd=None)


def test_fake_judge_scores_from_citations() -> None:
    judge = FakeDeterministicJudge()
    scores = judge.score(
        question="What is X?",
        answer="X is 1",
        contexts=("X is 1 according to doc",),
        citation_coverage=0.5,
    )
    assert scores.faithfulness == 0.5
    assert scores.response_relevancy == 1.0

    empty = judge.score(
        question="q",
        answer="   ",
        contexts=(),
        citation_coverage=0.0,
    )
    assert empty.response_relevancy == 0.0


def test_apply_llm_judge_adds_metrics_without_flipping_status() -> None:
    report = EvalRunReport(
        suite_id="s1",
        status="passed",
        metrics={"chat_citation_coverage": 1.0},
        thresholds={},
        cases=(
            EvalCaseResult(
                id="c1",
                kind="chat",
                status="passed",
                metrics={"citation_coverage": 1.0},
                answer="Grounded answer",
                context_snippets=("ctx",),
            ),
            EvalCaseResult(
                id="r1",
                kind="retrieval",
                status="passed",
                metrics={"hit": 1.0},
            ),
        ),
    )
    judged = apply_llm_judge(report, judge=FakeDeterministicJudge())
    assert judged.status == "passed"
    assert judged.metrics["judge_case_count"] == 1.0
    assert judged.metrics["judge_faithfulness_mean"] == 1.0
    assert judged.metrics["judge_response_relevancy_mean"] == 1.0
    chat = judged.cases[0]
    assert chat.metrics["judge_faithfulness"] == 1.0
    assert chat.metrics["judge_response_relevancy"] == 1.0
    # retrieval case untouched
    assert "judge_faithfulness" not in judged.cases[1].metrics


def test_prompt_judge_parses_json_and_records_usage() -> None:
    tracker = InMemoryProviderUsageTracker()

    def completer(prompt: str) -> str:
        assert "faithfulness" in prompt.lower() or "JSON" in prompt
        return '{"faithfulness": 0.8, "response_relevancy": 0.6}'

    judge = PromptLlmJudge(
        complete=completer,
        usage_tracker=tracker,
        budget_guard=ProviderBudgetGuard(max_cost_usd=1.0),
        provider="fake",
        model="judge-v1",
        estimated_cost_usd=0.01,
    )
    scores = judge.score(
        question="q",
        answer="a",
        contexts=("c",),
        citation_coverage=0.0,
    )
    assert scores == JudgeScores(faithfulness=0.8, response_relevancy=0.6)
    assert len(tracker.records) == 1
    assert tracker.records[0].operation == "eval_judge"
    assert tracker.records[0].outcome == "succeeded"


def test_prompt_judge_budget_blocks() -> None:
    tracker = InMemoryProviderUsageTracker()
    judge = PromptLlmJudge(
        complete=lambda _p: '{"faithfulness": 1.0, "response_relevancy": 1.0}',
        usage_tracker=tracker,
        budget_guard=ProviderBudgetGuard(max_cost_usd=0.001),
        provider="fake",
        model="judge-v1",
        estimated_cost_usd=0.5,
    )
    with pytest.raises(ProviderBudgetExceededError):
        judge.score(
            question="q",
            answer="a",
            contexts=("c",),
            citation_coverage=1.0,
        )
    assert tracker.records[0].outcome == "blocked"
