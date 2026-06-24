"""Tests for provider model discovery clients."""

from __future__ import annotations

import json

import httpx

from adaptive_rag.db.models import ProviderConnection
from adaptive_rag.provider_models import HTTPProviderModelLister


def test_openai_compatible_model_lister_reads_ids_and_metadata() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(
            200,
            json={
                "data": [
                    {
                        "id": "qwen-plus",
                        "object": "model",
                        "owned_by": "system",
                    },
                    {
                        "id": "text-embedding-v4",
                        "pricing": {"input_per_million_tokens_usd": 0.07},
                    },
                ]
            },
        )

    lister = HTTPProviderModelLister(
        timeout_seconds=3.0,
        transport=httpx.MockTransport(handler),
    )
    connection = ProviderConnection(
        connection_id="qwen-hosted",
        provider="qwen",
        connection_type="hosted",
        base_url="https://dashscope.example.test/compatible-mode/v1",
        capabilities_json=["chat", "dense_embedding"],
    )

    models = lister.list_models(connection, api_key="sk-hosted-secret")

    assert str(requests[0].url) == (
        "https://dashscope.example.test/compatible-mode/v1/models"
    )
    assert requests[0].headers["Authorization"] == "Bearer sk-hosted-secret"
    assert [model.model_id for model in models] == [
        "qwen-plus",
        "text-embedding-v4",
    ]
    assert models[0].metadata == {
        "id": "qwen-plus",
        "object": "model",
        "owned_by": "system",
    }
    assert models[0].pricing is None
    assert models[1].pricing == {"input_per_million_tokens_usd": 0.07}


def test_model_lister_rejects_responses_without_data_array() -> None:
    lister = HTTPProviderModelLister(
        timeout_seconds=3.0,
        transport=httpx.MockTransport(
            lambda _request: httpx.Response(200, content=json.dumps({"items": []}))
        ),
    )
    connection = ProviderConnection(
        connection_id="local-chat",
        provider="local_openai_compatible",
        connection_type="local",
        base_url="http://localhost:11434/v1",
        capabilities_json=["chat"],
    )

    try:
        lister.list_models(connection, api_key=None)
    except ValueError as exc:
        assert str(exc) == "provider model response missing data"
        return

    raise AssertionError("Expected model listing failure")


def test_model_lister_reads_dashscope_output_data_shape() -> None:
    lister = HTTPProviderModelLister(
        timeout_seconds=3.0,
        transport=httpx.MockTransport(
            lambda _request: httpx.Response(
                200,
                json={"output": {"data": [{"id": "qwen-max"}]}},
            )
        ),
    )
    connection = ProviderConnection(
        connection_id="qwen-native",
        provider="qwen",
        connection_type="hosted",
        base_url="https://dashscope.aliyuncs.com/api/v1",
        capabilities_json=["chat"],
    )

    models = lister.list_models(connection, api_key="sk-hosted-secret")

    assert [model.model_id for model in models] == ["qwen-max"]
