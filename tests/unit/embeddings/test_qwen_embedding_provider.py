from __future__ import annotations

import httpx
import pytest

from adaptive_rag.db.models import EMBEDDING_DIMENSIONS
from adaptive_rag.embeddings import (
    QwenDenseEmbeddingProvider,
    QwenEmbeddingProviderError,
    QwenHTTPEmbeddingClient,
    QwenSparseEmbeddingProvider,
    SparseEmbeddingVector,
)
from adaptive_rag.provider_usage import (
    InMemoryProviderUsageTracker,
    ProviderBudgetExceededError,
    ProviderBudgetGuard,
    ProviderPriceCatalog,
)


class RecordingQwenEmbeddingClient:
    def __init__(self, embeddings: list[list[float]]) -> None:
        self.embeddings = embeddings
        self.calls: list[dict[str, object]] = []

    def embed_texts(
        self,
        *,
        model: str,
        texts: list[str],
        dimensions: int,
    ) -> list[list[float]]:
        self.calls.append(
            {
                "model": model,
                "texts": list(texts),
                "dimensions": dimensions,
            }
        )
        return self.embeddings[: len(texts)]


class RecordingQwenSparseEmbeddingClient:
    def __init__(self, embeddings: list[SparseEmbeddingVector]) -> None:
        self.embeddings = embeddings
        self.calls: list[dict[str, object]] = []

    def embed_sparse_texts(
        self,
        *,
        model: str,
        texts: list[str],
        text_type: str,
        dimensions: int,
    ) -> list[SparseEmbeddingVector]:
        self.calls.append(
            {
                "model": model,
                "texts": list(texts),
                "text_type": text_type,
                "dimensions": dimensions,
            }
        )
        return self.embeddings[: len(texts)]


def _vector(value: float = 0.1) -> list[float]:
    return [value] * EMBEDDING_DIMENSIONS


def test_qwen_provider_calls_client_with_canonical_dimension() -> None:
    client = RecordingQwenEmbeddingClient([_vector(0.2), _vector(0.3)])
    provider = QwenDenseEmbeddingProvider(
        model_name="text-embedding-v4",
        client=client,
    )

    embeddings = provider.embed_texts(["alpha", "beta"])

    assert embeddings == [_vector(0.2), _vector(0.3)]
    assert client.calls == [
        {
            "model": "text-embedding-v4",
            "texts": ["alpha", "beta"],
            "dimensions": EMBEDDING_DIMENSIONS,
        }
    ]


def test_qwen_provider_rejects_wrong_embedding_count() -> None:
    provider = QwenDenseEmbeddingProvider(
        model_name="text-embedding-v4",
        client=RecordingQwenEmbeddingClient([_vector(0.2)]),
    )

    with pytest.raises(
        QwenEmbeddingProviderError,
        match="qwen embedding provider returned wrong count",
    ):
        provider.embed_texts(["alpha", "beta"])


def test_qwen_provider_rejects_wrong_embedding_dimension() -> None:
    provider = QwenDenseEmbeddingProvider(
        model_name="text-embedding-v4",
        client=RecordingQwenEmbeddingClient([[0.1, 0.2, 0.3]]),
    )

    with pytest.raises(
        QwenEmbeddingProviderError,
        match="qwen embedding dimension mismatch",
    ):
        provider.embed_texts(["alpha"])


def test_qwen_sparse_provider_calls_client_with_document_and_query_text_type() -> None:
    sparse = SparseEmbeddingVector(
        indices=(1, 42),
        values=(0.25, 0.75),
        tokens=("alpha", "beta"),
    )
    client = RecordingQwenSparseEmbeddingClient([sparse, sparse])
    provider = QwenSparseEmbeddingProvider(
        model_name="text-embedding-v4",
        client=client,
    )

    assert provider.embed_documents(["alpha", "beta"]) == [sparse, sparse]
    assert provider.embed_query("alpha") == sparse
    assert client.calls == [
        {
            "model": "text-embedding-v4",
            "texts": ["alpha", "beta"],
            "text_type": "document",
            "dimensions": EMBEDDING_DIMENSIONS,
        },
        {
            "model": "text-embedding-v4",
            "texts": ["alpha"],
            "text_type": "query",
            "dimensions": EMBEDDING_DIMENSIONS,
        },
    ]


def test_qwen_sparse_provider_rejects_wrong_embedding_count() -> None:
    provider = QwenSparseEmbeddingProvider(
        model_name="text-embedding-v4",
        client=RecordingQwenSparseEmbeddingClient([]),
    )

    with pytest.raises(
        QwenEmbeddingProviderError,
        match="qwen sparse embedding provider returned wrong count",
    ):
        provider.embed_documents(["alpha"])


def test_qwen_http_client_posts_dashscope_embedding_payload() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(
            200,
            json={
                "output": {
                    "embeddings": [
                        {"text_index": 0, "embedding": _vector(0.4)},
                        {"text_index": 1, "embedding": _vector(0.5)},
                    ]
                }
            },
        )

    client = QwenHTTPEmbeddingClient(
        api_key="sk-test",
        base_url="https://example.test/api/v1/services/embeddings/text-embedding",
        timeout_seconds=5.0,
        max_retries=0,
        transport=httpx.MockTransport(handler),
    )

    embeddings = client.embed_texts(
        model="text-embedding-v4",
        texts=["alpha", "beta"],
        dimensions=EMBEDDING_DIMENSIONS,
    )

    assert embeddings == [_vector(0.4), _vector(0.5)]
    assert len(requests) == 1
    request = requests[0]
    assert request.method == "POST"
    assert str(request.url) == (
        "https://example.test/api/v1/services/embeddings/text-embedding"
    )
    assert request.headers["authorization"] == "Bearer sk-test"
    assert request.read() == (
        b'{"model":"text-embedding-v4","input":{"texts":["alpha","beta"]},'
        b'"parameters":{"dimension":1024}}'
    )


def test_qwen_http_client_posts_dashscope_sparse_embedding_payload() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(
            200,
            headers={"x-request-id": "req_sparse"},
            json={
                "output": {
                    "embeddings": [
                        {
                            "text_index": 1,
                            "sparse_embedding": [
                                {"index": 7, "value": 0.5, "token": "beta"}
                            ],
                        },
                        {
                            "text_index": 0,
                            "sparse_embedding": [
                                {"index": 3, "value": 0.25, "token": "alpha"},
                                {"index": 9, "value": 0.75, "token": "omega"},
                            ],
                        },
                    ]
                },
                "usage": {"total_tokens": 100},
            },
        )

    tracker = InMemoryProviderUsageTracker()
    client = QwenHTTPEmbeddingClient(
        api_key="sk-test",
        base_url="https://example.test/api/v1/services/embeddings/text-embedding",
        timeout_seconds=5.0,
        max_retries=0,
        transport=httpx.MockTransport(handler),
        usage_tracker=tracker,
        price_catalog=ProviderPriceCatalog(
            embedding_input_price_per_million_tokens_usd=0.13,
        ),
    )

    embeddings = client.embed_sparse_texts(
        model="text-embedding-v4",
        texts=["alpha", "beta"],
        text_type="document",
        dimensions=EMBEDDING_DIMENSIONS,
    )

    assert embeddings == [
        SparseEmbeddingVector(
            indices=(3, 9),
            values=(0.25, 0.75),
            tokens=("alpha", "omega"),
        ),
        SparseEmbeddingVector(indices=(7,), values=(0.5,), tokens=("beta",)),
    ]
    assert len(requests) == 1
    request = requests[0]
    assert request.method == "POST"
    assert str(request.url) == (
        "https://example.test/api/v1/services/embeddings/text-embedding"
    )
    assert request.headers["authorization"] == "Bearer sk-test"
    assert request.read() == (
        b'{"model":"text-embedding-v4","input":{"texts":["alpha","beta"]},'
        b'"parameters":{"dimension":1024,"output_type":"sparse",'
        b'"text_type":"document"}}'
    )
    assert len(tracker.records) == 1
    record = tracker.records[0]
    assert record.operation == "embedding"
    assert record.usage.input_tokens == 100
    assert record.request_id == "req_sparse"


def test_qwen_http_client_accepts_openai_compatible_embedding_shape() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(
            200,
            json={
                "data": [
                    {"index": 1, "embedding": _vector(0.6)},
                    {"index": 0, "embedding": _vector(0.7)},
                ]
            },
        )

    client = QwenHTTPEmbeddingClient(
        api_key="sk-test",
        base_url="https://example.test/compatible-mode/v1",
        timeout_seconds=5.0,
        max_retries=0,
        transport=httpx.MockTransport(handler),
    )

    embeddings = client.embed_texts(
        model="text-embedding-v4",
        texts=["alpha", "beta"],
        dimensions=EMBEDDING_DIMENSIONS,
    )

    assert embeddings == [_vector(0.7), _vector(0.6)]
    assert len(requests) == 1
    request = requests[0]
    assert str(request.url) == "https://example.test/compatible-mode/v1/embeddings"
    assert request.read() == (
        b'{"model":"text-embedding-v4","input":["alpha","beta"],'
        b'"dimensions":1024}'
    )


def test_qwen_http_client_reports_http_errors_without_secret() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"message": "bad key"})

    client = QwenHTTPEmbeddingClient(
        api_key="sk-secret-value",
        base_url="https://example.test/v1",
        timeout_seconds=5.0,
        max_retries=0,
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(QwenEmbeddingProviderError) as exc_info:
        client.embed_texts(
            model="text-embedding-v4",
            texts=["alpha"],
            dimensions=EMBEDDING_DIMENSIONS,
        )

    message = str(exc_info.value)
    assert "qwen embedding request failed with status 401" in message
    assert "sk-secret-value" not in message


def test_qwen_http_embedding_client_repr_hides_api_key() -> None:
    client = QwenHTTPEmbeddingClient(
        api_key="sk-secret-value",
        base_url="https://example.test/v1",
        timeout_seconds=5.0,
        max_retries=0,
    )

    representation = repr(client)

    assert "https://example.test/v1" in representation
    assert "sk-secret-value" not in representation


def test_qwen_http_embedding_client_records_usage_and_estimated_cost() -> None:
    tracker = InMemoryProviderUsageTracker()

    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            headers={"x-request-id": "req_embed"},
            json={
                "data": [{"index": 0, "embedding": _vector(0.8)}],
                "usage": {"prompt_tokens": 100, "total_tokens": 100},
            },
        )

    client = QwenHTTPEmbeddingClient(
        api_key="sk-test",
        base_url="https://example.test/compatible-mode/v1",
        timeout_seconds=5.0,
        max_retries=0,
        transport=httpx.MockTransport(handler),
        usage_tracker=tracker,
        price_catalog=ProviderPriceCatalog(
            embedding_input_price_per_million_tokens_usd=0.13,
        ),
    )

    client.embed_texts(
        model="text-embedding-v4",
        texts=["alpha"],
        dimensions=EMBEDDING_DIMENSIONS,
    )

    assert len(tracker.records) == 1
    record = tracker.records[0]
    assert record.provider == "qwen"
    assert record.model == "text-embedding-v4"
    assert record.operation == "embedding"
    assert record.outcome == "succeeded"
    assert record.usage.input_tokens == 100
    assert record.usage_source == "provider_reported"
    assert record.estimated_cost_usd == 0.000013
    assert record.request_id == "req_embed"


def test_qwen_http_embedding_client_blocks_when_budget_is_exceeded() -> None:
    tracker = InMemoryProviderUsageTracker()

    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "data": [{"index": 0, "embedding": _vector(0.8)}],
                "usage": {"prompt_tokens": 100, "total_tokens": 100},
            },
        )

    client = QwenHTTPEmbeddingClient(
        api_key="sk-test",
        base_url="https://example.test/compatible-mode/v1",
        timeout_seconds=5.0,
        max_retries=0,
        transport=httpx.MockTransport(handler),
        usage_tracker=tracker,
        price_catalog=ProviderPriceCatalog(
            embedding_input_price_per_million_tokens_usd=0.13,
        ),
        budget_guard=ProviderBudgetGuard(max_cost_usd=0.000001),
    )

    with pytest.raises(ProviderBudgetExceededError):
        client.embed_texts(
            model="text-embedding-v4",
            texts=["alpha"],
            dimensions=EMBEDDING_DIMENSIONS,
        )

    assert len(tracker.records) == 1
    assert tracker.records[0].outcome == "blocked"
    assert tracker.records[0].estimated_cost_usd == 0.000013
