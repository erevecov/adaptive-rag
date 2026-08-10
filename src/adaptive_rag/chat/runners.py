"""Runners conversacionales deterministas para desarrollo local."""

from __future__ import annotations

from uuid import UUID

from adaptive_rag.chat.models import ChatRunnerOutput, ChatRunnerRequest
from adaptive_rag.chat.tools import ChatTools


class RetrievalGroundedChatRunner:
    """Runner local sin red que responde con evidencia recuperada."""

    # Accepts image attachments without network (test hook).
    model_capabilities: tuple[str, ...] = ("chat", "vision")
    fallback_model_capabilities: tuple[str, ...] = ()

    def run(
        self,
        request: ChatRunnerRequest,
        tools: ChatTools,
    ) -> ChatRunnerOutput:
        query = request.retrieval_query or request.message
        retrieval = tools.retrieval.search(
            query=query,
            limit=request.retrieval_limit,
            metadata_filter=request.metadata_filter,
        )
        cited_chunk_ids = tuple(
            UUID(result["chunk_id"]) for result in retrieval.results
        )
        image_count = sum(
            1
            for attachment in request.attachments
            if attachment.kind == "image" and attachment.image_data_url
        )
        if not retrieval.results:
            answer = "No retrieval results found."
            if image_count:
                answer = f"{answer}\nAttached images: {image_count}"
            return ChatRunnerOutput(
                answer=answer,
                cited_chunk_ids=(),
            )

        snippets = [
            result["citation"]["snippet"]
            for result in retrieval.results[:3]
        ]
        answer = "\n\n".join(snippets)
        if image_count:
            answer = f"{answer}\nAttached images: {image_count}"
        return ChatRunnerOutput(
            answer=answer,
            cited_chunk_ids=cited_chunk_ids,
        )
