"""Security: bulk source bodies must not appear on citation surfaces."""

from __future__ import annotations

from uuid import uuid4

from adaptive_rag.retrieval.dense import DenseRetrievalCitation
from adaptive_rag.retrieval.payloads import serialize_retrieval_result
from adaptive_rag.retrieval.service import RetrievalSearchResult
from adaptive_rag.retrieval.source_extra_metadata import (
    CITATION_SOURCE_EXTRA_METADATA_DENYLIST,
    sanitize_source_extra_metadata,
)


def test_sanitize_strips_content_and_content_base64() -> None:
    raw = {
        "title": "notes.md",
        "filename": "notes.md",
        "url": "https://example.com/notes.md",
        "owner": "alice",
        "language": "en",
        "content": "# Full body that must never leak",
        "content_base64": "c2VjcmV0LWJvZHk=",
        "provider": "fake",
    }
    cleaned = sanitize_source_extra_metadata(raw)
    assert cleaned is not None
    assert "content" not in cleaned
    assert "content_base64" not in cleaned
    assert cleaned["title"] == "notes.md"
    assert cleaned["filename"] == "notes.md"
    assert cleaned["url"] == "https://example.com/notes.md"
    assert cleaned["owner"] == "alice"
    assert cleaned["language"] == "en"
    assert cleaned["provider"] == "fake"
    # Source dict is not mutated.
    assert "content" in raw
    assert "content_base64" in raw


def test_sanitize_none_and_empty() -> None:
    assert sanitize_source_extra_metadata(None) is None
    assert sanitize_source_extra_metadata({}) == {}
    only_bulk = sanitize_source_extra_metadata(
        {"content": "secret", "content_base64": "YQ=="}
    )
    assert only_bulk == {}


def test_denylist_covers_known_bulk_keys() -> None:
    assert "content" in CITATION_SOURCE_EXTRA_METADATA_DENYLIST
    assert "content_base64" in CITATION_SOURCE_EXTRA_METADATA_DENYLIST


def _result_with_source_extra(
    source_extra_metadata: dict | None,
    *,
    source_tags: tuple[str, ...] = ("docs", "policy"),
    source_type: str = "markdown",
) -> RetrievalSearchResult:
    chunk_id = uuid4()
    citation = DenseRetrievalCitation(
        source_id=uuid4(),
        source_type=source_type,
        source_external_id="alpha.md",
        source_tags=source_tags,
        source_extra_metadata=source_extra_metadata,
        document_id=uuid4(),
        document_stable_id="alpha-doc",
        document_version_id=uuid4(),
        document_version_number=1,
        chunk_id=chunk_id,
        char_start=0,
        char_end=12,
        snippet="snippet text",
        section_metadata={"heading": "Alpha"},
    )
    return RetrievalSearchResult(
        chunk_id=chunk_id,
        distance=0.1,
        score=0.9,
        citation=citation,
        embedding_metadata={"provider": "fake"},
        strategy="dense",
    )


def test_serialize_strips_content_from_source_extra_metadata() -> None:
    result = _result_with_source_extra(
        {
            "title": "Alpha",
            "content": "# Secret full source body with API_KEY=sk-test",
            "content_base64": "c2VjcmV0",
            "filename": "alpha.md",
        }
    )
    payload = serialize_retrieval_result(result)
    meta = payload["citation"]["source_extra_metadata"]
    assert meta is not None
    assert "content" not in meta
    assert "content_base64" not in meta
    assert meta["title"] == "Alpha"
    assert meta["filename"] == "alpha.md"
    # tags / source_type remain on the citation (not only in extra_metadata).
    assert payload["citation"]["source_tags"] == ["docs", "policy"]
    assert payload["citation"]["source_type"] == "markdown"
    assert payload["citation"]["snippet"] == "snippet text"


def test_serialize_preserves_safe_metadata_and_tags() -> None:
    result = _result_with_source_extra(
        {"title": "near.md", "language": "es"},
        source_tags=("public",),
        source_type="url",
    )
    payload = serialize_retrieval_result(result)
    assert payload["citation"]["source_extra_metadata"] == {
        "title": "near.md",
        "language": "es",
    }
    assert payload["citation"]["source_tags"] == ["public"]
    assert payload["citation"]["source_type"] == "url"


def test_serialize_handles_none_source_extra_metadata() -> None:
    result = _result_with_source_extra(None)
    payload = serialize_retrieval_result(result)
    assert payload["citation"]["source_extra_metadata"] is None
