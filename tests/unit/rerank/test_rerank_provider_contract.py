import pytest

from adaptive_rag.rerank import (
    FakeRerankProvider,
    RerankCandidate,
    RerankProviderError,
    RerankRequest,
)


def test_fake_reranker_scores_and_limits_candidates_deterministically() -> None:
    provider = FakeRerankProvider()
    request = RerankRequest(
        query="alpha policy",
        candidates=(
            RerankCandidate(candidate_id="chunk-1", text="beta reference"),
            RerankCandidate(candidate_id="chunk-2", text="alpha policy details"),
            RerankCandidate(candidate_id="chunk-3", text="alpha appendix"),
        ),
        top_k=2,
    )

    result = provider.rerank(request)

    assert result.provider_name == "fake"
    assert result.model_name == "fake-rerank-v1"
    assert provider.requests == (request,)
    assert [score.candidate_id for score in result.scores] == ["chunk-2", "chunk-3"]
    assert [score.original_rank for score in result.scores] == [2, 3]
    assert [score.rerank_rank for score in result.scores] == [1, 2]
    assert result.scores[0].score > result.scores[1].score


@pytest.mark.parametrize(
    ("request_kwargs", "error_match"),
    [
        (
            {
                "query": "",
                "candidates": (RerankCandidate(candidate_id="chunk-1", text="text"),),
                "top_k": 1,
            },
            "rerank query must not be empty",
        ),
        (
            {
                "query": "alpha",
                "candidates": (),
                "top_k": 1,
            },
            "rerank candidates must not be empty",
        ),
        (
            {
                "query": "alpha",
                "candidates": (RerankCandidate(candidate_id="chunk-1", text="text"),),
                "top_k": 0,
            },
            "rerank top_k must be positive",
        ),
        (
            {
                "query": "alpha",
                "candidates": (RerankCandidate(candidate_id="chunk-1", text="text"),),
                "top_k": 2,
            },
            "rerank top_k must be less than or equal to candidate count",
        ),
        (
            {
                "query": "alpha",
                "candidates": (
                    RerankCandidate(candidate_id="chunk-1", text="first"),
                    RerankCandidate(candidate_id="chunk-1", text="second"),
                ),
                "top_k": 1,
            },
            "rerank candidate ids must be unique",
        ),
    ],
)
def test_rerank_request_rejects_invalid_inputs(
    request_kwargs: dict[str, object],
    error_match: str,
) -> None:
    with pytest.raises(RerankProviderError, match=error_match):
        RerankRequest(**request_kwargs)


def test_rerank_candidate_rejects_missing_text() -> None:
    with pytest.raises(RerankProviderError, match="rerank candidate text is required"):
        RerankCandidate(candidate_id="chunk-1", text=" ")

