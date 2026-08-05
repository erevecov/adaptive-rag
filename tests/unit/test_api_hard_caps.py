"""Schema/service hard caps for lease seconds and retrieval limits."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from adaptive_rag.api.schemas.ingestion_ops import RunNextIngestionJobRequestBody
from adaptive_rag.api.schemas.retrieval import RetrievalSearchRequestBody
from adaptive_rag.db.models import CHAT_RETRIEVAL_MAX_LIMIT


def test_run_next_job_rejects_lease_seconds_above_one_hour() -> None:
    with pytest.raises(ValidationError) as excinfo:
        RunNextIngestionJobRequestBody(lease_seconds=3601)
    assert "lease_seconds" in str(excinfo.value)


def test_run_next_job_accepts_lease_seconds_at_bounds() -> None:
    low = RunNextIngestionJobRequestBody(lease_seconds=1)
    high = RunNextIngestionJobRequestBody(lease_seconds=3600)
    assert low.lease_seconds == 1
    assert high.lease_seconds == 3600


def test_run_next_job_rejects_lease_seconds_below_one() -> None:
    with pytest.raises(ValidationError) as excinfo:
        RunNextIngestionJobRequestBody(lease_seconds=0)
    assert "lease_seconds" in str(excinfo.value)


def test_retrieval_search_body_rejects_query_over_max_length() -> None:
    with pytest.raises(ValidationError) as excinfo:
        RetrievalSearchRequestBody(query="x" * 32_001)
    assert "query" in str(excinfo.value)


def test_retrieval_search_body_accepts_query_at_max_length() -> None:
    body = RetrievalSearchRequestBody(query="y" * 32_000)
    assert len(body.query) == 32_000


def test_retrieval_search_body_rejects_limit_above_max() -> None:
    with pytest.raises(ValidationError) as excinfo:
        RetrievalSearchRequestBody(
            query="hello",
            limit=CHAT_RETRIEVAL_MAX_LIMIT + 1,
        )
    assert "limit" in str(excinfo.value)


def test_retrieval_search_body_rejects_candidate_limit_above_max() -> None:
    with pytest.raises(ValidationError) as excinfo:
        RetrievalSearchRequestBody(
            query="hello",
            limit=1,
            rerank={"candidate_limit": CHAT_RETRIEVAL_MAX_LIMIT + 1},
        )
    assert "candidate_limit" in str(excinfo.value)
