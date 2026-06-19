"""Comandos CLI de providers live/fake."""

from __future__ import annotations

import json
from typing import Annotated
from uuid import UUID

import typer

from adaptive_rag.chat import ChatRequest, ChatService, ChatServiceError
from adaptive_rag.chat.qwen import QwenChatRunnerError
from adaptive_rag.cli.dependencies import (
    get_cli_chat_runner,
    get_cli_dense_embedding_provider,
)
from adaptive_rag.embeddings import QwenEmbeddingProviderError
from adaptive_rag.provider_runtime import ProviderConfigurationError
from adaptive_rag.provider_usage import ProviderBudgetExceededError
from adaptive_rag.retrieval import (
    DenseRetrievalCitation,
    RetrievalSearchRequest,
    RetrievalSearchResult,
)

app = typer.Typer(no_args_is_help=True)


@app.command("embedding-smoke")
def embedding_smoke(
    text: Annotated[str, typer.Option("--text")] = "Adaptive RAG smoke",
) -> None:
    provider = get_cli_dense_embedding_provider()
    try:
        embeddings = provider.embed_texts([text])
    except (
        ProviderBudgetExceededError,
        ProviderConfigurationError,
        QwenEmbeddingProviderError,
    ) as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(1) from exc

    typer.echo(
        json.dumps(
            {
                "provider": provider.provider_name,
                "model": provider.model_name,
                "dimensions": provider.dimensions,
                "input_count": 1,
                "embedding_count": len(embeddings),
            }
        )
    )


@app.command("chat-smoke")
def chat_smoke(
    message: Annotated[str, typer.Option("--message")] = "What supports alpha?",
    retrieval_limit: Annotated[int, typer.Option("--retrieval-limit")] = 1,
) -> None:
    project_id = UUID("00000000-0000-0000-0000-000000000001")
    runner = get_cli_chat_runner()
    service = ChatService(
        runner=runner,
        retrieval_service=_StaticSmokeRetrievalService(project_id=project_id),
    )
    try:
        response = service.respond(
            ChatRequest(
                project_id=project_id,
                message=message,
                retrieval_limit=retrieval_limit,
            )
        )
    except (
        ProviderBudgetExceededError,
        ProviderConfigurationError,
        QwenChatRunnerError,
        ChatServiceError,
    ) as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(1) from exc

    typer.echo(
        json.dumps(
            {
                "provider": getattr(runner, "provider_name", "fake"),
                "model": getattr(runner, "model_name", "retrieval-grounded-local-v1"),
                "answer": response.answer,
                "citation_count": len(response.citations),
                "tool_call_count": len(response.tool_calls),
            }
        )
    )


class _StaticSmokeRetrievalService:
    def __init__(self, *, project_id: UUID) -> None:
        self._project_id = project_id

    def search(
        self,
        request: RetrievalSearchRequest,
    ) -> list[RetrievalSearchResult]:
        return [_smoke_result()]


def _smoke_result() -> RetrievalSearchResult:
    chunk_id = UUID("00000000-0000-0000-0000-000000000101")
    snippet = "Alpha smoke evidence"
    citation = DenseRetrievalCitation(
        source_id=UUID("00000000-0000-0000-0000-000000000201"),
        source_type="markdown",
        source_external_id="smoke.md",
        source_tags=("smoke",),
        source_extra_metadata={"title": "Smoke"},
        document_id=UUID("00000000-0000-0000-0000-000000000301"),
        document_stable_id="smoke-doc",
        document_version_id=UUID("00000000-0000-0000-0000-000000000401"),
        document_version_number=1,
        chunk_id=chunk_id,
        char_start=0,
        char_end=len(snippet),
        snippet=snippet,
        section_metadata={"heading": "Smoke"},
    )
    return RetrievalSearchResult(
        chunk_id=chunk_id,
        distance=0.0,
        score=1.0,
        citation=citation,
        embedding_metadata=None,
    )
