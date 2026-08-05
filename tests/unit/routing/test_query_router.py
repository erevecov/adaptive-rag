"""Unit tests for rule-based query router."""

from __future__ import annotations

from adaptive_rag.routing import RuleBasedQueryRouter


def test_greetings_skip_retrieval() -> None:
    router = RuleBasedQueryRouter()
    for query in ("Hello!", "thanks", "  hi  ", "how are you?"):
        decision = router.route(query)
        assert decision.route == "skip_retrieval", query


def test_factual_defaults_to_dense_sparse() -> None:
    decision = RuleBasedQueryRouter().route("What is Adaptive RAG indexing path?")
    assert decision.route == "dense_sparse"
    assert decision.strategy == "dense_sparse"


def test_graph_ready_vs_fallback() -> None:
    router = RuleBasedQueryRouter()
    query = "How is Project A related to Service B?"
    ready = router.route(query, graph_ready=True)
    not_ready = router.route(query, graph_ready=False)
    assert ready.route == "graph"
    assert not_ready.route == "dense_sparse"
    assert not_ready.reason == "graph_pattern_graph_not_ready"
