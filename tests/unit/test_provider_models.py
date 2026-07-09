"""Tests for provider model discovery clients."""

from __future__ import annotations

import json

import httpx
import pytest

from adaptive_rag.db.models import ProviderConnection
from adaptive_rag.provider_models import HTTPProviderModelLister


def _lister_returning(payload: object, *, status_code: int = 200) -> tuple[
    HTTPProviderModelLister, ProviderConnection
]:
    lister = HTTPProviderModelLister(
        timeout_seconds=3.0,
        transport=httpx.MockTransport(
            lambda _request: httpx.Response(status_code, json=payload)
        ),
    )
    connection = ProviderConnection(
        connection_id="local-chat",
        provider="local_openai_compatible",
        connection_type="local",
        base_url="http://localhost:11434/v1",
        capabilities_json=["chat"],
    )
    return lister, connection


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


def test_qwen_model_lister_infers_safe_capabilities_when_provider_is_silent() -> None:
    lister = HTTPProviderModelLister(
        timeout_seconds=3.0,
        transport=httpx.MockTransport(
            lambda _request: httpx.Response(
                200,
                json={
                    "data": [
                        {"id": "qwen-plus"},
                        {"id": "text-embedding-v4"},
                        {"id": "qwen3-rerank"},
                    ]
                },
            )
        ),
    )
    connection = ProviderConnection(
        connection_id="qwen-all",
        provider="qwen",
        connection_type="hosted",
        base_url="https://dashscope.example.test/compatible-mode/v1",
        capabilities_json=[
            "chat",
            "dense_embedding",
            "sparse_embedding",
            "rerank",
        ],
    )

    models = lister.list_models(connection, api_key="sk-hosted-secret")

    assert [(model.model_id, model.capabilities) for model in models] == [
        ("qwen-plus", ("chat",)),
        ("text-embedding-v4", ("dense_embedding", "sparse_embedding")),
        ("qwen3-rerank", ("rerank",)),
    ]


def test_fake_provider_returns_deterministic_catalog_without_http() -> None:
    lister = HTTPProviderModelLister(timeout_seconds=1.0)
    connection = ProviderConnection(
        connection_id="fake-all",
        provider="fake",
        connection_type="fake",
        base_url=None,
        capabilities_json=["chat", "dense_embedding", "unknown_capability"],
    )

    models = lister.list_models(connection, api_key=None)

    catalog = {model.model_id: model for model in models}
    assert set(catalog) == {"retrieval-grounded-local-v1", "fake-embedding-v1"}
    assert catalog["retrieval-grounded-local-v1"].capabilities == ("chat",)
    assert catalog["fake-embedding-v1"].capabilities == ("dense_embedding",)
    assert catalog["fake-embedding-v1"].metadata == {"source": "fake"}


def test_list_models_rejects_unsupported_provider() -> None:
    lister = HTTPProviderModelLister(timeout_seconds=1.0)
    connection = ProviderConnection(
        connection_id="anthropic",
        provider="anthropic",  # type: ignore[arg-type]
        connection_type="hosted",
        base_url="https://api.anthropic.test/v1",
        capabilities_json=["chat"],
    )

    with pytest.raises(ValueError, match="unsupported provider model listing"):
        lister.list_models(connection, api_key=None)


def test_list_models_requires_base_url() -> None:
    lister = HTTPProviderModelLister(timeout_seconds=1.0)
    connection = ProviderConnection(
        connection_id="qwen-no-url",
        provider="qwen",
        connection_type="hosted",
        base_url=None,
        capabilities_json=["chat"],
    )

    with pytest.raises(ValueError, match="requires base_url"):
        lister.list_models(connection, api_key=None)


def test_list_models_raises_on_http_error_status() -> None:
    lister, connection = _lister_returning({"data": []}, status_code=503)

    with pytest.raises(ValueError, match="failed with status 503"):
        lister.list_models(connection, api_key=None)


def test_list_models_raises_on_invalid_json_body() -> None:
    lister = HTTPProviderModelLister(
        timeout_seconds=1.0,
        transport=httpx.MockTransport(
            lambda _request: httpx.Response(200, content=b"not-json")
        ),
    )
    connection = ProviderConnection(
        connection_id="local-chat",
        provider="local_openai_compatible",
        connection_type="local",
        base_url="http://localhost:11434/v1",
        capabilities_json=["chat"],
    )

    with pytest.raises(ValueError, match="invalid JSON"):
        lister.list_models(connection, api_key=None)


def test_models_endpoint_not_duplicated_when_base_url_already_targets_models() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json={"data": []})

    lister = HTTPProviderModelLister(
        timeout_seconds=1.0,
        transport=httpx.MockTransport(handler),
    )
    connection = ProviderConnection(
        connection_id="local-chat",
        provider="local_openai_compatible",
        connection_type="local",
        base_url="http://localhost:11434/v1/models/",
        capabilities_json=["chat"],
    )

    lister.list_models(connection, api_key=None)

    assert str(requests[0].url) == "http://localhost:11434/v1/models"


def test_list_models_rejects_non_list_data_payload() -> None:
    lister, connection = _lister_returning({"data": {"id": "x"}})

    with pytest.raises(ValueError, match="missing data"):
        lister.list_models(connection, api_key=None)


def test_list_models_rejects_non_object_response_body() -> None:
    lister, connection = _lister_returning(["qwen-plus"])

    with pytest.raises(ValueError, match="missing data"):
        lister.list_models(connection, api_key=None)


def test_list_models_rejects_non_object_model_item() -> None:
    lister, connection = _lister_returning({"data": ["qwen-plus"]})

    with pytest.raises(ValueError, match="item must be an object"):
        lister.list_models(connection, api_key=None)


@pytest.mark.parametrize("bad_id", [None, "", "   ", 42])
def test_list_models_rejects_items_missing_valid_id(bad_id: object) -> None:
    lister, connection = _lister_returning({"data": [{"id": bad_id}]})

    with pytest.raises(ValueError, match="missing id"):
        lister.list_models(connection, api_key=None)


def test_capabilities_are_filtered_and_normalized_to_canonical_order() -> None:
    lister, connection = _lister_returning(
        {
            "data": [
                {
                    "id": "  local-multi  ",
                    "capabilities": [
                        "rerank",
                        "chat",
                        "not-a-capability",
                        7,
                        " dense_embedding ",
                    ],
                }
            ]
        }
    )

    models = lister.list_models(connection, api_key=None)

    assert len(models) == 1
    model = models[0]
    assert model.model_id == "local-multi"
    assert model.capabilities == ("chat", "dense_embedding", "rerank")


def test_pricing_read_from_price_key_when_pricing_absent() -> None:
    lister, connection = _lister_returning(
        {"data": [{"id": "local-chat", "price": {"input_usd": 0.01}}]}
    )

    models = lister.list_models(connection, api_key=None)

    assert models[0].pricing == {"input_usd": 0.01}


def test_headers_omit_authorization_without_api_key() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json={"data": []})

    lister = HTTPProviderModelLister(
        timeout_seconds=1.0,
        transport=httpx.MockTransport(handler),
    )
    connection = ProviderConnection(
        connection_id="local-chat",
        provider="local_openai_compatible",
        connection_type="local",
        base_url="http://localhost:11434/v1",
        capabilities_json=["chat"],
    )

    lister.list_models(connection, api_key=None)

    assert "Authorization" not in requests[0].headers
