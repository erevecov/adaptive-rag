"""Rutas HTTP de chat/tool calling."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from adaptive_rag.api.dependencies import get_chat_service
from adaptive_rag.api.schemas.chat import ChatRequestBody, ChatResponseBody
from adaptive_rag.chat import ChatService, ChatServiceError

router = APIRouter(
    prefix="/projects/{project_id}/chat",
    tags=["chat"],
)


@router.post("", response_model=ChatResponseBody)
def chat(
    project_id: UUID,
    body: ChatRequestBody,
    service: Annotated[ChatService, Depends(get_chat_service)],
) -> ChatResponseBody:
    try:
        response = service.respond(body.to_service_request(project_id))
    except ChatServiceError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc
    return ChatResponseBody.from_chat_response(response)
