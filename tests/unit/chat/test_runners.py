"""Tests de runners conversacionales locales."""

from __future__ import annotations

from uuid import UUID, uuid4

from adaptive_rag.chat import ChatRunnerRequest, RetrievalGroundedChatRunner
from adaptive_rag.chat.tools import ChatRetrievalTool, ChatTools
from adaptive_rag.retrieval import (
    DenseRetrievalCitation,
    RetrievalSearchRequest,
    RetrievalSearchResult,
)


class RecordingRetrievalService:
    def __init__(self, results: list[RetrievalSearchResult]) -> None:
        self.results = results
        self.requests: list[RetrievalSearchRequest] = []

    def search(
        self,
        request: RetrievalSearchRequest,
    ) -> list[RetrievalSearchResult]:
        self.requests.append(request)
        return list(self.results)


def test_retrieval_grounded_runner_answers_with_retrieved_snippets() -> None:
    project_id = uuid4()
    first_chunk_id = uuid4()
    second_chunk_id = uuid4()
    retrieval = RecordingRetrievalService(
        [
            _retrieval_result(
                chunk_id=first_chunk_id,
                snippet="First evidence",
            ),
            _retrieval_result(
                chunk_id=second_chunk_id,
                snippet="Second evidence",
            ),
        ]
    )
    tools = ChatTools(
        retrieval=ChatRetrievalTool(
            retrieval_service=retrieval,
            project_id=project_id,
            default_limit=2,
            default_metadata_filter=None,
        )
    )

    output = RetrievalGroundedChatRunner().run(
        ChatRunnerRequest(
            project_id=project_id,
            message="What supports alpha?",
            retrieval_limit=2,
            metadata_filter=None,
        ),
        tools,
    )

    assert retrieval.requests == [
        RetrievalSearchRequest(
            project_id=project_id,
            query="What supports alpha?",
            limit=2,
            metadata_filter=None,
        )
    ]
    assert output.answer == "First evidence\n\nSecond evidence"
    assert output.cited_chunk_ids == (first_chunk_id, second_chunk_id)


def test_retrieval_grounded_runner_handles_empty_retrieval_results() -> None:
    project_id = uuid4()
    retrieval = RecordingRetrievalService([])
    tools = ChatTools(
        retrieval=ChatRetrievalTool(
            retrieval_service=retrieval,
            project_id=project_id,
            default_limit=2,
            default_metadata_filter=None,
        )
    )

    output = RetrievalGroundedChatRunner().run(
        ChatRunnerRequest(
            project_id=project_id,
            message="What supports alpha?",
            retrieval_limit=2,
            metadata_filter=None,
        ),
        tools,
    )

    assert output.answer == "No retrieval results found."
    assert output.cited_chunk_ids == ()


def _retrieval_result(
    *,
    chunk_id: UUID,
    snippet: str,
) -> RetrievalSearchResult:
    citation = DenseRetrievalCitation(
        source_id=uuid4(),
        source_type="markdown",
        source_external_id="alpha.md",
        source_tags=("docs",),
        source_extra_metadata={"title": "Alpha"},
        document_id=uuid4(),
        document_stable_id="alpha-doc",
        document_version_id=uuid4(),
        document_version_number=1,
        chunk_id=chunk_id,
        char_start=0,
        char_end=len(snippet),
        snippet=snippet,
        section_metadata={"heading": "Alpha"},
    )
    return RetrievalSearchResult(
        chunk_id=chunk_id,
        distance=0.2,
        score=1 / 1.2,
        citation=citation,
        embedding_metadata=None,
    )
