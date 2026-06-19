from __future__ import annotations

import json

import httpx

from adaptive_rag.chat.qwen import QwenHTTPChatClient


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
