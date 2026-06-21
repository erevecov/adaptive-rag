"""Rutas HTTP de chat/tool calling."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from adaptive_rag.api.dependencies import get_chat_service, get_session
from adaptive_rag.api.schemas.chat import (
    ChatRequestBody,
    ChatResponseBody,
    ChatSessionDetailResponse,
    ChatSessionListResponse,
)
from adaptive_rag.chat import ChatService, ChatServiceError
from adaptive_rag.db.repositories import ChatAuditRepository

router = APIRouter(
    prefix="/projects/{project_id}/chat",
    tags=["chat"],
)


@router.get("/sessions", response_model=ChatSessionListResponse)
def list_chat_sessions(
    project_id: UUID,
    session: Annotated[Session, Depends(get_session)],
    status: Annotated[str | None, Query()] = None,
    limit: Annotated[int, Query()] = 20,
    cursor: Annotated[str | None, Query()] = None,
) -> ChatSessionListResponse:
    try:
        page = ChatAuditRepository(session).list_session_summaries(
            project_id=project_id,
            status=status,
            limit=limit,
            cursor=cursor,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return ChatSessionListResponse.from_summary_page(page)


@router.get("/sessions/{session_id}", response_model=ChatSessionDetailResponse)
def get_chat_session(
    project_id: UUID,
    session_id: UUID,
    session: Annotated[Session, Depends(get_session)],
) -> ChatSessionDetailResponse:
    detail = ChatAuditRepository(session).get_session_detail(
        project_id=project_id,
        session_id=session_id,
    )
    if detail is None:
        raise HTTPException(status_code=404, detail="chat session not found")
    return ChatSessionDetailResponse.from_detail(detail)


@router.post("", response_model=ChatResponseBody)
def chat(
    project_id: UUID,
    body: ChatRequestBody,
    service: Annotated[ChatService, Depends(get_chat_service)],
    session: Annotated[Session, Depends(get_session)],
) -> ChatResponseBody:
    try:
        response = service.respond(body.to_service_request(project_id))
        session.commit()
    except ChatServiceError as exc:
        _commit_or_rollback_chat_error(session)
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc
    except Exception:
        _commit_or_rollback_chat_error(session)
        raise
    return ChatResponseBody.from_chat_response(response)


def _commit_or_rollback_chat_error(session: Session) -> None:
    try:
        session.commit()
    except Exception:
        session.rollback()
