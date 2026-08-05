"""Unit tests for verbatim source-chunk regurgitation filtering."""

from __future__ import annotations

from uuid import uuid4

from adaptive_rag.chat import ChatRequest, ChatService
from adaptive_rag.chat.models import ChatRunnerOutput, ChatRunnerRequest
from adaptive_rag.chat.tools import ChatTools
from adaptive_rag.security.source_regurgitation import (
    DEFAULT_MIN_SPAN_CHARS,
    REGURGITATION_MARKER,
    filter_source_regurgitation,
    find_regurgitation_spans,
)

# Long enough to exceed the conservative 200-char threshold.
_CHUNK = (
    "The Adaptive RAG retrieval pipeline indexes each document version into "
    "semantic markdown chunks with reproducible character offsets so citations "
    "can be anchored back to the normalized source text without ambiguity. "
    "Dense and sparse candidates are fused with RRF before optional rerank."
)

assert len(_CHUNK) >= DEFAULT_MIN_SPAN_CHARS


def test_verbatim_chunk_span_is_redacted() -> None:
    answer = f"Based on the docs:\n\n{_CHUNK}\n\nThat covers the indexing path."
    cleaned, count = filter_source_regurgitation(answer, [_CHUNK])
    assert count == 1
    assert _CHUNK not in cleaned
    assert REGURGITATION_MARKER in cleaned
    assert "Based on the docs:" in cleaned
    assert "That covers the indexing path." in cleaned


def test_paraphrase_passes_unchanged() -> None:
    paraphrase = (
        "Adaptive RAG breaks documents into semantic markdown pieces and keeps "
        "stable offsets so each citation points at the original normalized text. "
        "It then blends dense and sparse hits with reciprocal rank fusion and "
        "may apply an optional reranker afterward."
    )
    cleaned, count = filter_source_regurgitation(paraphrase, [_CHUNK])
    assert count == 0
    assert cleaned == paraphrase


def test_short_exact_quote_below_threshold_passes() -> None:
    short = _CHUNK[:80]
    answer = f"It says: {short} — interesting."
    cleaned, count = filter_source_regurgitation(answer, [_CHUNK])
    assert count == 0
    assert cleaned == answer
    assert short in cleaned


def test_empty_sources_are_passthrough() -> None:
    answer = _CHUNK
    cleaned, count = filter_source_regurgitation(answer, [])
    assert count == 0
    assert cleaned is answer or cleaned == answer


def test_find_spans_merges_overlapping_matches() -> None:
    # Two overlapping windows of the same long dump should merge to one span.
    answer = f"PREFIX {_CHUNK} SUFFIX"
    spans = find_regurgitation_spans(answer, [_CHUNK, _CHUNK[10:]])
    assert len(spans) == 1
    start, end = spans[0]
    assert answer[start:end] == _CHUNK


def test_min_span_override_catches_shorter_dump() -> None:
    snippet = "exactly-this-phrase-is-copied"
    answer = f"Here: {snippet} end."
    cleaned, count = filter_source_regurgitation(
        answer,
        [snippet],
        min_span_chars=20,
    )
    assert count == 1
    assert snippet not in cleaned
    assert REGURGITATION_MARKER in cleaned


class _RegurgRunner:
    def run(self, request: ChatRunnerRequest, tools: ChatTools) -> ChatRunnerOutput:
        del request
        # Simulate a retrieval hit, then echo its snippet verbatim in the answer.
        result = tools.retrieval.search(query="pipeline")
        snippet = result.results[0]["citation"]["snippet"]
        return ChatRunnerOutput(
            answer=f"Verbatim dump follows.\n\n{snippet}\n\nDone.",
            cited_chunk_ids=(),
        )


class _SnippetRetrieval:
    def search(self, request):  # type: ignore[no-untyped-def]
        del request
        from adaptive_rag.retrieval.dense import DenseRetrievalCitation
        from adaptive_rag.retrieval.service import RetrievalSearchResult

        chunk_id = uuid4()
        citation = DenseRetrievalCitation(
            source_id=uuid4(),
            source_type="markdown",
            source_external_id="doc-1",
            source_tags=(),
            source_extra_metadata=None,
            document_id=uuid4(),
            document_stable_id="stable-1",
            document_version_id=uuid4(),
            document_version_number=1,
            chunk_id=chunk_id,
            char_start=0,
            char_end=len(_CHUNK),
            snippet=_CHUNK,
            section_metadata=None,
        )
        return [
            RetrievalSearchResult(
                chunk_id=chunk_id,
                distance=0.1,
                score=0.9,
                citation=citation,
                embedding_metadata=None,
                strategy="dense",
            )
        ]


def test_chat_service_redacts_regurgitated_retrieved_snippet() -> None:
    service = ChatService(
        runner=_RegurgRunner(),
        retrieval_service=_SnippetRetrieval(),
    )
    response = service.respond(
        ChatRequest(project_id=uuid4(), message="explain the pipeline")
    )
    assert _CHUNK not in response.answer
    assert REGURGITATION_MARKER in response.answer
    assert "Verbatim dump follows." in response.answer
