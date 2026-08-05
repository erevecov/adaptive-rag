"""Chat retrieval tool honors query routing."""

from __future__ import annotations

from uuid import uuid4

from adaptive_rag.chat.tools import ChatRetrievalTool
from adaptive_rag.retrieval import RetrievalSearchRequest


class _RecordingRetrieval:
    def __init__(self) -> None:
        self.requests: list[RetrievalSearchRequest] = []

    def search(self, request: RetrievalSearchRequest) -> list:
        self.requests.append(request)
        return []


def test_skip_route_does_not_call_retrieval_service() -> None:
    retrieval = _RecordingRetrieval()
    tool = ChatRetrievalTool(
        retrieval_service=retrieval,
        project_id=uuid4(),
        default_limit=5,
        default_metadata_filter=None,
    )
    result = tool.search(query="Hello!")
    assert result.results == ()
    assert retrieval.requests == []


def test_dense_sparse_route_uses_strategy() -> None:
    retrieval = _RecordingRetrieval()
    tool = ChatRetrievalTool(
        retrieval_service=retrieval,
        project_id=uuid4(),
        default_limit=5,
        default_metadata_filter=None,
    )
    tool.search(query="What is Adaptive RAG indexing?")
    assert len(retrieval.requests) == 1
    assert retrieval.requests[0].strategy == "dense_sparse"


def test_graph_route_uses_graph_strategy_when_ready() -> None:
    retrieval = _RecordingRetrieval()
    tool = ChatRetrievalTool(
        retrieval_service=retrieval,
        project_id=uuid4(),
        default_limit=5,
        default_metadata_filter=None,
        graph_ready=True,
    )
    tool.search(query="How is Project A related to Service B?")
    assert len(retrieval.requests) == 1
    assert retrieval.requests[0].strategy == "graph"


def test_graph_pattern_falls_back_when_not_ready() -> None:
    retrieval = _RecordingRetrieval()
    tool = ChatRetrievalTool(
        retrieval_service=retrieval,
        project_id=uuid4(),
        default_limit=5,
        default_metadata_filter=None,
        graph_ready=False,
    )
    tool.search(query="How is Project A related to Service B?")
    assert len(retrieval.requests) == 1
    assert retrieval.requests[0].strategy == "dense_sparse"
