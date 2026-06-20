from __future__ import annotations

import json

import httpx
import pytest

from adaptive_rag.provider_usage import (
    InMemoryProviderUsageTracker,
    ProviderBudgetExceededError,
    ProviderBudgetGuard,
    ProviderPriceCatalog,
)
from adaptive_rag.rerank import (
    QwenHTTPRerankClient,
    QwenRerankProviderError,
    RerankCandidate,
    RerankRequest,
)


def _request() -> RerankRequest:
    return RerankRequest(
        query="What supports alpha?",
        candidates=(
            RerankCandidate(candidate_id="chunk-1", text="Beta only"),
            RerankCandidate(candidate_id="chunk-2", text="Alpha evidence"),
            RerankCandidate(candidate_id="chunk-3", text="Alpha appendix"),
        ),
        top_k=2,
    )


def test_qwen_http_rerank_client_posts_compatible_rerank_payload() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["authorization"] = request.headers["Authorization"]
        captured["payload"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={
                "output": {
                    "results": [
                        {"index": 1, "relevance_score": 0.91},
                        {"index": 2, "relevance_score": 0.72},
                    ]
                },
                "usage": {"total_tokens": 79},
                "request_id": "req_rerank",
            },
        )

    client = QwenHTTPRerankClient(
        api_key="sk-test",
        base_url="https://dashscope-intl.aliyuncs.com/compatible-api/v1",
        timeout_seconds=7.5,
        max_retries=1,
        transport=httpx.MockTransport(handler),
    )

    result = client.rerank(model="qwen3-rerank", request=_request())

    assert captured["url"] == (
        "https://dashscope-intl.aliyuncs.com/compatible-api/v1/reranks"
    )
    assert captured["authorization"] == "Bearer sk-test"
    assert captured["payload"] == {
        "model": "qwen3-rerank",
        "documents": ["Beta only", "Alpha evidence", "Alpha appendix"],
        "query": "What supports alpha?",
        "top_n": 2,
        "instruct": (
            "Given a web search query, retrieve relevant passages that answer "
            "the query."
        ),
    }
    assert result.provider_name == "qwen"
    assert result.model_name == "qwen3-rerank"
    assert [score.candidate_id for score in result.scores] == ["chunk-2", "chunk-3"]
    assert [score.original_rank for score in result.scores] == [2, 3]
    assert [score.rerank_rank for score in result.scores] == [1, 2]
    assert [score.score for score in result.scores] == [0.91, 0.72]
    assert result.scores[0].metadata == {"request_id": "req_rerank"}


def test_qwen_http_rerank_client_maps_workspace_compatible_base_to_dashscope_path() -> (
    None
):
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["payload"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={
                "output": {
                    "results": [
                        {"index": 1, "relevance_score": 0.91},
                    ]
                }
            },
        )

    client = QwenHTTPRerankClient(
        api_key="sk-test",
        base_url="https://workspace.example.test/compatible-mode/v1",
        timeout_seconds=7.5,
        max_retries=0,
        transport=httpx.MockTransport(handler),
    )

    client.rerank(model="qwen3-rerank", request=_request())

    assert captured["url"] == (
        "https://workspace.example.test/api/v1/services/rerank/text-rerank/"
        "text-rerank"
    )
    assert captured["payload"] == {
        "model": "qwen3-rerank",
        "input": {
            "query": "What supports alpha?",
            "documents": ["Beta only", "Alpha evidence", "Alpha appendix"],
        },
        "parameters": {
            "top_n": 2,
            "instruct": (
                "Given a web search query, retrieve relevant passages that answer "
                "the query."
            ),
        },
    }


def test_qwen_http_rerank_client_reports_http_errors_without_secret() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"message": "bad key"})

    client = QwenHTTPRerankClient(
        api_key="sk-secret-value",
        base_url="https://dashscope-intl.aliyuncs.com/compatible-api/v1",
        timeout_seconds=5.0,
        max_retries=0,
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(QwenRerankProviderError) as exc_info:
        client.rerank(model="qwen3-rerank", request=_request())

    message = str(exc_info.value)
    assert "qwen rerank request failed with status 401" in message
    assert "sk-secret-value" not in message


def test_qwen_http_rerank_client_rejects_unknown_result_index() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"output": {"results": [{"index": 99, "relevance_score": 0.9}]}},
        )

    client = QwenHTTPRerankClient(
        api_key="sk-test",
        base_url="https://dashscope-intl.aliyuncs.com/compatible-api/v1",
        timeout_seconds=5.0,
        max_retries=0,
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(
        QwenRerankProviderError,
        match="qwen rerank returned unknown candidate index",
    ):
        client.rerank(model="qwen3-rerank", request=_request())


def test_qwen_http_rerank_client_records_usage_and_estimated_cost() -> None:
    tracker = InMemoryProviderUsageTracker()

    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "output": {"results": [{"index": 1, "relevance_score": 0.91}]},
                "usage": {"total_tokens": 100},
                "request_id": "req_rerank",
            },
        )

    client = QwenHTTPRerankClient(
        api_key="sk-test",
        base_url="https://dashscope-intl.aliyuncs.com/compatible-api/v1",
        timeout_seconds=5.0,
        max_retries=0,
        transport=httpx.MockTransport(handler),
        usage_tracker=tracker,
        price_catalog=ProviderPriceCatalog(
            rerank_input_price_per_million_tokens_usd=0.1,
        ),
    )

    client.rerank(model="qwen3-rerank", request=_request())

    assert len(tracker.records) == 1
    record = tracker.records[0]
    assert record.provider == "qwen"
    assert record.model == "qwen3-rerank"
    assert record.operation == "rerank"
    assert record.outcome == "succeeded"
    assert record.usage.input_tokens == 100
    assert record.usage.total_tokens == 100
    assert record.usage.input_count == 3
    assert record.usage_source == "provider_reported"
    assert record.estimated_cost_usd == 0.00001
    assert record.request_id == "req_rerank"


def test_qwen_http_rerank_client_blocks_when_budget_is_exceeded() -> None:
    tracker = InMemoryProviderUsageTracker()

    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "output": {"results": [{"index": 1, "relevance_score": 0.91}]},
                "usage": {"total_tokens": 100},
            },
        )

    client = QwenHTTPRerankClient(
        api_key="sk-test",
        base_url="https://dashscope-intl.aliyuncs.com/compatible-api/v1",
        timeout_seconds=5.0,
        max_retries=0,
        transport=httpx.MockTransport(handler),
        usage_tracker=tracker,
        price_catalog=ProviderPriceCatalog(
            rerank_input_price_per_million_tokens_usd=0.1,
        ),
        budget_guard=ProviderBudgetGuard(max_cost_usd=0.000001),
    )

    with pytest.raises(ProviderBudgetExceededError):
        client.rerank(model="qwen3-rerank", request=_request())

    assert len(tracker.records) == 1
    assert tracker.records[0].outcome == "blocked"
    assert tracker.records[0].estimated_cost_usd == 0.00001
