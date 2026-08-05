"""MCP stdio tools via FastMCP: search, ask, ingest_text, list_*."""

from __future__ import annotations

import json
from typing import Any
from uuid import UUID

from mcp.server.fastmcp import FastMCP

from adaptive_rag import authoring, ingestion_ops
from adaptive_rag.chat import ChatRequest, ChatService, RetrievalGroundedChatRunner
from adaptive_rag.cli.dependencies import (
    get_cli_chat_runner,
    get_cli_dense_embedding_provider,
    get_cli_sparse_embedding_provider,
)
from adaptive_rag.db.session import session_scope
from adaptive_rag.embeddings import (
    FakeDenseEmbeddingProvider,
    FakeSparseEmbeddingProvider,
)
from adaptive_rag.retrieval import RetrievalSearchRequest, RetrievalService
from adaptive_rag.retrieval.payloads import serialize_retrieval_results

REQUIRED_TOOL_NAMES: tuple[str, ...] = (
    "list_projects",
    "list_sources",
    "search",
    "ask",
    "ingest_text",
)

mcp = FastMCP("adaptive-rag")


def _providers() -> tuple[Any, Any, Any]:
    try:
        return (
            get_cli_dense_embedding_provider(),
            get_cli_sparse_embedding_provider(),
            get_cli_chat_runner(),
        )
    except Exception:
        return (
            FakeDenseEmbeddingProvider(),
            FakeSparseEmbeddingProvider(),
            RetrievalGroundedChatRunner(),
        )


@mcp.tool()
def list_projects() -> str:
    """List Adaptive RAG projects accessible locally."""

    with session_scope() as session:
        projects = authoring.list_projects(session)
        return json.dumps(
            {"items": [authoring.project_payload(p) for p in projects]},
            default=str,
        )


@mcp.tool()
def list_sources(project_id: str) -> str:
    """List sources for a project UUID."""

    with session_scope() as session:
        sources = authoring.list_sources(session, project_id=UUID(project_id))
        return json.dumps(
            {"items": [authoring.source_payload(s) for s in sources]},
            default=str,
        )


@mcp.tool()
def search(project_id: str, query: str, limit: int = 5) -> str:
    """Dense_sparse retrieval search over a project corpus."""

    dense, sparse, _runner = _providers()
    with session_scope() as session:
        results = RetrievalService(
            session, provider=dense, sparse_provider=sparse
        ).search(
            RetrievalSearchRequest(
                project_id=UUID(project_id),
                query=query,
                limit=max(1, limit),
                strategy="dense_sparse",
            )
        )
        return json.dumps(
            {"results": serialize_retrieval_results(results)},
            default=str,
        )


@mcp.tool()
def ask(project_id: str, question: str) -> str:
    """Ask a grounded chat question over a project corpus."""

    dense, sparse, runner = _providers()
    with session_scope() as session:
        response = ChatService(
            runner=runner,
            retrieval_service=RetrievalService(
                session, provider=dense, sparse_provider=sparse
            ),
        ).respond(
            ChatRequest(
                project_id=UUID(project_id),
                message=question,
                retrieval_limit=5,
            )
        )
        return json.dumps(
            {
                "answer": response.answer,
                "citation_count": len(response.citations),
            },
            default=str,
        )


@mcp.tool()
def ingest_text(project_id: str, external_id: str, content: str) -> str:
    """Create a markdown source and enqueue public ingest_source."""

    with session_scope() as session:
        source = authoring.create_source(
            session,
            project_id=UUID(project_id),
            source_type="markdown",
            external_id=external_id,
            extra_metadata={"content": content},
        )
        job = ingestion_ops.enqueue_source_ingestion(
            session, project_id=UUID(project_id), source_id=source.id
        )
        session.commit()
        return json.dumps(
            {
                "source": authoring.source_payload(source),
                "job_id": str(job.id),
                "job_type": job.job_type,
            },
            default=str,
        )


def tool_names() -> tuple[str, ...]:
    return REQUIRED_TOOL_NAMES


def build_server() -> FastMCP:
    return mcp


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
