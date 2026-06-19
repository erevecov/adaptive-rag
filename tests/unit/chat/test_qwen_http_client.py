from __future__ import annotations

import json

import httpx
import pytest

from adaptive_rag.chat.qwen import QwenHTTPChatClient
from adaptive_rag.provider_usage import (
    InMemoryProviderUsageTracker,
    ProviderBudgetExceededError,
    ProviderBudgetGuard,
    ProviderPriceCatalog,
)


def test_qwen_http_chat_client_posts_openai_compatible_chat_request() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["authorization"] = request.headers["Authorization"]
        captured["payload"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": '{"answer":"ok","cited_chunk_ids":[]}',
                        }
                    }
                ]
            },
        )

    client = QwenHTTPChatClient(
        api_key="sk-test",
        base_url="https://example.test/compatible-mode/v1",
        timeout_seconds=7.5,
        max_retries=1,
        transport=httpx.MockTransport(handler),
    )

    response = client.create_chat_completion(
        model="qwen-plus",
        messages=[{"role": "user", "content": "hello"}],
        tools=[{"type": "function", "function": {"name": "retrieval.search"}}],
    )

    assert captured["url"] == (
        "https://example.test/compatible-mode/v1/chat/completions"
    )
    assert captured["authorization"] == "Bearer sk-test"
    assert captured["payload"] == {
        "model": "qwen-plus",
        "messages": [{"role": "user", "content": "hello"}],
        "tools": [
            {
                "type": "function",
                "function": {"name": "retrieval.search"},
            }
        ],
        "tool_choice": {
            "type": "function",
            "function": {"name": "retrieval.search"},
        },
        "temperature": 0,
    }
    assert response["choices"][0]["message"]["content"] == (
        '{"answer":"ok","cited_chunk_ids":[]}'
    )


def test_qwen_http_chat_client_omits_tool_choice_without_tools() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["payload"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": '{"answer":"ok","cited_chunk_ids":[]}',
                        }
                    }
                ]
            },
        )

    client = QwenHTTPChatClient(
        api_key="sk-test",
        base_url="https://example.test/compatible-mode/v1",
        timeout_seconds=7.5,
        max_retries=1,
        transport=httpx.MockTransport(handler),
    )

    client.create_chat_completion(
        model="qwen-plus",
        messages=[{"role": "user", "content": "hello"}],
    )

    assert captured["payload"] == {
        "model": "qwen-plus",
        "messages": [{"role": "user", "content": "hello"}],
        "temperature": 0,
    }


def test_qwen_http_chat_client_records_usage_and_estimated_cost() -> None:
    tracker = InMemoryProviderUsageTracker()

    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            headers={"x-request-id": "req_chat"},
            json={
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": '{"answer":"ok","cited_chunk_ids":[]}',
                        }
                    }
                ],
                "usage": {
                    "prompt_tokens": 1_000,
                    "completion_tokens": 500,
                    "total_tokens": 1_500,
                },
            },
        )

    client = QwenHTTPChatClient(
        api_key="sk-test",
        base_url="https://example.test/compatible-mode/v1",
        timeout_seconds=7.5,
        max_retries=1,
        transport=httpx.MockTransport(handler),
        usage_tracker=tracker,
        price_catalog=ProviderPriceCatalog(
            chat_input_price_per_million_tokens_usd=2.0,
            chat_output_price_per_million_tokens_usd=6.0,
        ),
    )

    client.create_chat_completion(
        model="qwen-plus",
        messages=[{"role": "user", "content": "hello"}],
    )

    assert len(tracker.records) == 1
    record = tracker.records[0]
    assert record.provider == "qwen"
    assert record.model == "qwen-plus"
    assert record.operation == "chat"
    assert record.outcome == "succeeded"
    assert record.duration_ms >= 0
    assert record.usage.input_tokens == 1_000
    assert record.usage.output_tokens == 500
    assert record.usage_source == "provider_reported"
    assert record.estimated_cost_usd == 0.005
    assert record.request_id == "req_chat"


def test_qwen_http_chat_client_blocks_response_when_budget_is_exceeded() -> None:
    tracker = InMemoryProviderUsageTracker()

    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": '{"answer":"ok","cited_chunk_ids":[]}',
                        }
                    }
                ],
                "usage": {
                    "prompt_tokens": 1_000,
                    "completion_tokens": 500,
                    "total_tokens": 1_500,
                },
            },
        )

    client = QwenHTTPChatClient(
        api_key="sk-test",
        base_url="https://example.test/compatible-mode/v1",
        timeout_seconds=7.5,
        max_retries=1,
        transport=httpx.MockTransport(handler),
        usage_tracker=tracker,
        price_catalog=ProviderPriceCatalog(
            chat_input_price_per_million_tokens_usd=2.0,
            chat_output_price_per_million_tokens_usd=6.0,
        ),
        budget_guard=ProviderBudgetGuard(max_cost_usd=0.001),
    )

    with pytest.raises(ProviderBudgetExceededError):
        client.create_chat_completion(
            model="qwen-plus",
            messages=[{"role": "user", "content": "hello"}],
        )

    assert len(tracker.records) == 1
    assert tracker.records[0].outcome == "blocked"
    assert tracker.records[0].estimated_cost_usd == 0.005
