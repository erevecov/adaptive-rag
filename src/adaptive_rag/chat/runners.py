"""Runners conversacionales deterministas para desarrollo local."""

from __future__ import annotations

from uuid import UUID

from adaptive_rag.chat.models import ChatRunnerOutput, ChatRunnerRequest
from adaptive_rag.chat.tools import ChatTools


class RetrievalGroundedChatRunner:
    """Runner local sin red que responde con evidencia recuperada."""

    def run(
        self,
        request: ChatRunnerRequest,
        tools: ChatTools,
    ) -> ChatRunnerOutput:
        retrieval = tools.retrieval.search(
            query=request.message,
            limit=request.retrieval_limit,
            metadata_filter=request.metadata_filter,
        )
        cited_chunk_ids = tuple(
            UUID(result["chunk_id"]) for result in retrieval.results
        )
        if not retrieval.results:
            return ChatRunnerOutput(
                answer="No retrieval results found.",
                cited_chunk_ids=(),
            )

        snippets = [
            result["citation"]["snippet"]
            for result in retrieval.results[:3]
        ]
        return ChatRunnerOutput(
            answer="\n\n".join(snippets),
            cited_chunk_ids=cited_chunk_ids,
        )
