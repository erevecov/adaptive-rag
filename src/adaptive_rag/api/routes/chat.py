"""Rutas HTTP de chat/tool calling."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from adaptive_rag.api.dependencies import (
    get_chat_service,
    get_current_user,
    get_project_access,
    get_project_admin_access,
    get_session,
)
from adaptive_rag.api.schemas.chat import (
    ChatObservabilitySummaryResponse,
    ChatRequestBody,
    ChatResponseBody,
    ChatSessionDetailResponse,
    ChatSessionListResponse,
    ChatSessionTitleUpdateBody,
    ChatSessionTitleUpdateResponse,
)
from adaptive_rag.auth import CurrentPrincipal
from adaptive_rag.chat import ChatService, ChatServiceError
from adaptive_rag.chat.streaming import ChatStreamEvent, serialize_chat_stream_event
from adaptive_rag.db.models import Project
from adaptive_rag.db.repositories import (
    ChatAuditRepository,
    ChatObservabilityRepository,
    ChatRetrievalSettingsRepository,
)

router = APIRouter(
    prefix="/projects/{project_id}/chat",
    tags=["chat"],
)


@router.get("/observability/summary", response_model=ChatObservabilitySummaryResponse)
def get_chat_observability_summary(
    project_id: UUID,
    session: Annotated[Session, Depends(get_session)],
    _access: Annotated[tuple[Project, str], Depends(get_project_admin_access)],
    created_at_from: Annotated[datetime | None, Query()] = None,
    created_at_to: Annotated[datetime | None, Query()] = None,
    status: Annotated[str | None, Query()] = None,
) -> ChatObservabilitySummaryResponse:
    try:
        summary = ChatObservabilityRepository(session).get_summary(
            project_id=project_id,
            created_at_from=created_at_from,
            created_at_to=created_at_to,
            status=status,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return ChatObservabilitySummaryResponse.from_summary(summary)


@router.get("/sessions", response_model=ChatSessionListResponse)
def list_chat_sessions(
    project_id: UUID,
    session: Annotated[Session, Depends(get_session)],
    current: Annotated[CurrentPrincipal, Depends(get_current_user)],
    _access: Annotated[tuple[Project, str], Depends(get_project_access)],
    status: Annotated[str | None, Query()] = None,
    archived: Annotated[bool, Query()] = False,
    limit: Annotated[int, Query()] = 20,
    cursor: Annotated[str | None, Query()] = None,
) -> ChatSessionListResponse:
    try:
        page = ChatAuditRepository(session).list_session_summaries(
            project_id=project_id,
            user_id=_history_user_id(current),
            status=status,
            archived=archived,
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
    current: Annotated[CurrentPrincipal, Depends(get_current_user)],
    _access: Annotated[tuple[Project, str], Depends(get_project_access)],
) -> ChatSessionDetailResponse:
    detail = ChatAuditRepository(session).get_session_detail(
        project_id=project_id,
        session_id=session_id,
        user_id=_history_user_id(current),
    )
    if detail is None:
        raise HTTPException(status_code=404, detail="chat session not found")
    return ChatSessionDetailResponse.from_detail(detail)


@router.patch(
    "/sessions/{session_id}/title",
    response_model=ChatSessionTitleUpdateResponse,
)
def update_chat_session_title(
    project_id: UUID,
    session_id: UUID,
    body: ChatSessionTitleUpdateBody,
    session: Annotated[Session, Depends(get_session)],
    current: Annotated[CurrentPrincipal, Depends(get_current_user)],
    _access: Annotated[tuple[Project, str], Depends(get_project_access)],
) -> ChatSessionTitleUpdateResponse:
    try:
        chat_session = ChatAuditRepository(session).update_session_title(
            project_id=project_id,
            session_id=session_id,
            user_id=_history_user_id(current),
            title=body.title,
        )
        session.commit()
    except ValueError as exc:
        session.rollback()
        if str(exc) == "session title must not be empty":
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        raise HTTPException(status_code=404, detail="chat session not found") from exc
    return ChatSessionTitleUpdateResponse.from_session(chat_session)


@router.post("/sessions/{session_id}/archive", status_code=204)
def archive_chat_session(
    project_id: UUID,
    session_id: UUID,
    session: Annotated[Session, Depends(get_session)],
    current: Annotated[CurrentPrincipal, Depends(get_current_user)],
    _access: Annotated[tuple[Project, str], Depends(get_project_access)],
) -> Response:
    try:
        ChatAuditRepository(session).archive_session(
            project_id=project_id,
            session_id=session_id,
            user_id=_history_user_id(current),
        )
        session.commit()
    except ValueError as exc:
        session.rollback()
        raise HTTPException(status_code=404, detail="chat session not found") from exc
    return Response(status_code=204)


@router.post("/sessions/{session_id}/unarchive", status_code=204)
def unarchive_chat_session(
    project_id: UUID,
    session_id: UUID,
    session: Annotated[Session, Depends(get_session)],
    current: Annotated[CurrentPrincipal, Depends(get_current_user)],
    _access: Annotated[tuple[Project, str], Depends(get_project_access)],
) -> Response:
    try:
        ChatAuditRepository(session).unarchive_session(
            project_id=project_id,
            session_id=session_id,
            user_id=_history_user_id(current),
        )
        session.commit()
    except ValueError as exc:
        session.rollback()
        raise HTTPException(status_code=404, detail="chat session not found") from exc
    return Response(status_code=204)


@router.post("/stream")
def stream_chat(
    project_id: UUID,
    body: ChatRequestBody,
    service: Annotated[ChatService, Depends(get_chat_service)],
    session: Annotated[Session, Depends(get_session)],
    current: Annotated[CurrentPrincipal, Depends(get_current_user)],
    _access: Annotated[tuple[Project, str], Depends(get_project_access)],
) -> StreamingResponse:
    try:
        chat_retrieval_settings = ChatRetrievalSettingsRepository(
            session
        ).get_effective_project_settings(project_id)
        events = service.stream(
            body.to_service_request(
                project_id,
                chat_retrieval_settings=chat_retrieval_settings,
                user_id=current.user_id,
            )
        )
    except ChatServiceError as exc:
        _commit_or_rollback_chat_error(session)
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc
    return StreamingResponse(
        _stream_chat_events(events, session),
        media_type="text/event-stream",
    )


@router.post("", response_model=ChatResponseBody)
def chat(
    project_id: UUID,
    body: ChatRequestBody,
    service: Annotated[ChatService, Depends(get_chat_service)],
    session: Annotated[Session, Depends(get_session)],
    current: Annotated[CurrentPrincipal, Depends(get_current_user)],
    _access: Annotated[tuple[Project, str], Depends(get_project_access)],
) -> ChatResponseBody:
    try:
        chat_retrieval_settings = ChatRetrievalSettingsRepository(
            session
        ).get_effective_project_settings(project_id)
        response = service.respond(
            body.to_service_request(
                project_id,
                chat_retrieval_settings=chat_retrieval_settings,
                user_id=current.user_id,
            )
        )
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


def _stream_chat_events(
    events: Iterator[ChatStreamEvent],
    session: Session,
) -> Iterator[str]:
    try:
        for event in events:
            yield serialize_chat_stream_event(event)
        session.commit()
    except Exception:
        _commit_or_rollback_chat_error(session)
        raise


def _commit_or_rollback_chat_error(session: Session) -> None:
    try:
        session.commit()
    except Exception:
        session.rollback()


def _history_user_id(current: CurrentPrincipal) -> UUID | None:
    return None if current.is_superadmin else current.user_id
