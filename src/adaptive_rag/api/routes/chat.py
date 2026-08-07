"""Rutas HTTP de chat/tool calling."""

from __future__ import annotations

import logging
import threading
import time
from collections import defaultdict, deque
from collections.abc import Iterator
from dataclasses import replace
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
from adaptive_rag.chat import ChatRequest, ChatService, ChatServiceError
from adaptive_rag.chat.streaming import ChatStreamEvent, serialize_chat_stream_event
from adaptive_rag.db.models import Project
from adaptive_rag.db.repositories import (
    ChatAuditRepository,
    ChatObservabilityRepository,
    ChatRetrievalSettingsRepository,
)

logger = logging.getLogger(__name__)

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


@router.delete("/sessions/{session_id}", status_code=204)
def delete_chat_session(
    project_id: UUID,
    session_id: UUID,
    session: Annotated[Session, Depends(get_session)],
    current: Annotated[CurrentPrincipal, Depends(get_current_user)],
    _access: Annotated[tuple[Project, str], Depends(get_project_access)],
) -> Response:
    try:
        ChatAuditRepository(session).delete_session(
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
    rate_key = _chat_rate_key(project_id=project_id, user_id=current.user_id)
    if not _try_acquire_chat_rate(rate_key):
        raise HTTPException(
            status_code=429,
            detail={
                "code": "chat_rate_limited",
                "message": (
                    "Too many chat requests. Wait a moment before sending another."
                ),
                "retryable": True,
                "detail": (
                    "Too many chat requests. Wait a moment before sending another."
                ),
            },
        )
    flight_key = _chat_flight_key(
        project_id=project_id,
        user_id=current.user_id,
        session_id=body.session_id,
    )
    user_flight_key = _chat_user_flight_key(
        project_id=project_id, user_id=current.user_id
    )
    if not _try_acquire_chat_user_flight(user_flight_key):
        raise HTTPException(
            status_code=409,
            detail={
                "code": "chat_user_in_flight",
                "message": (
                    "You already have a chat turn in progress. "
                    "Wait for it to finish or cancel it first."
                ),
                "retryable": True,
                "detail": (
                    "You already have a chat turn in progress. "
                    "Wait for it to finish or cancel it first."
                ),
            },
        )
    if not _try_acquire_chat_flight(flight_key):
        _release_chat_user_flight(user_flight_key)
        raise HTTPException(
            status_code=409,
            detail={
                "code": "chat_in_flight",
                "message": (
                    "A chat turn is already in progress for this session. "
                    "Wait for it to finish or cancel it first."
                ),
                "retryable": True,
                "detail": (
                    "A chat turn is already in progress for this session. "
                    "Wait for it to finish or cancel it first."
                ),
            },
        )
    try:
        chat_retrieval_settings = ChatRetrievalSettingsRepository(
            session
        ).get_effective_project_settings(project_id)
        request = body.to_service_request(
            project_id,
            chat_retrieval_settings=chat_retrieval_settings,
            user_id=current.user_id,
        )
        request = _with_approved_user_memory(
            session,
            request=request,
            user_id=current.user_id,
            project_id=project_id,
        )
        events = service.stream(request)
    except ChatServiceError as exc:
        _release_chat_flight(flight_key)
        _release_chat_user_flight(user_flight_key)
        _commit_or_rollback_chat_error(session)
        raise HTTPException(
            status_code=exc.status_code,
            detail=exc.to_payload().as_dict(),
        ) from exc
    except Exception:
        _release_chat_flight(flight_key)
        _release_chat_user_flight(user_flight_key)
        raise
    return StreamingResponse(
        _stream_chat_events(
            events,
            session,
            flight_key=flight_key,
            user_flight_key=user_flight_key,
        ),
        media_type="text/event-stream",
    )


@router.post("", response_model=ChatResponseBody, response_model_exclude_none=True)
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
        request = body.to_service_request(
            project_id,
            chat_retrieval_settings=chat_retrieval_settings,
            user_id=current.user_id,
        )
        request = _with_approved_user_memory(
            session,
            request=request,
            user_id=current.user_id,
            project_id=project_id,
        )
        response = service.respond(request)
        session.commit()
    except ChatServiceError as exc:
        _commit_or_rollback_chat_error(session)
        raise HTTPException(
            status_code=exc.status_code,
            detail=exc.to_payload().as_dict(),
        ) from exc
    except Exception:
        _commit_or_rollback_chat_error(session)
        raise
    return ChatResponseBody.from_chat_response(response)


def _stream_chat_events(
    events: Iterator[ChatStreamEvent],
    session: Session,
    *,
    flight_key: str | None = None,
    user_flight_key: str | None = None,
) -> Iterator[str]:
    try:
        for event in events:
            yield serialize_chat_stream_event(event)
            # Persist session + user message as soon as the client learns the
            # session_id so cancel/disconnect cannot leave a ghost id in the UI.
            if event.event == "session_started":
                session.commit()
        session.commit()
    except GeneratorExit:
        # Client aborted; keep any durable fail_session/user-message writes.
        try:
            session.commit()
        except Exception as exc:
            logger.warning(
                "chat_stream_disconnect_commit_failed; rolling back",
                extra={"error_type": type(exc).__name__},
                exc_info=exc,
            )
            session.rollback()
        raise
    except Exception:
        _commit_or_rollback_chat_error(session)
        raise
    finally:
        if flight_key is not None:
            _release_chat_flight(flight_key)
        if user_flight_key is not None:
            _release_chat_user_flight(user_flight_key)


# Per-process guards: session in-flight, user in-flight, and request rate.
_CHAT_FLIGHT_LOCK = threading.Lock()
_CHAT_IN_FLIGHT: set[str] = set()
_CHAT_USER_IN_FLIGHT: set[str] = set()
_CHAT_RATE_WINDOWS: dict[str, deque[float]] = defaultdict(deque)
# Max chat stream starts per user/project in a rolling 60s window.
_CHAT_RATE_LIMIT_PER_MINUTE = 20
# Max concurrent streams per user/project (across sessions).
_CHAT_MAX_USER_IN_FLIGHT = 1


def _chat_flight_key(
    *,
    project_id: UUID,
    user_id: UUID | None,
    session_id: UUID | None,
) -> str | None:
    """Only continuations (known session_id) are session-concurrency-guarded."""

    if session_id is None:
        return None
    owner = str(user_id) if user_id is not None else "anonymous"
    return f"{project_id}:{owner}:{session_id}"


def _chat_user_flight_key(
    *,
    project_id: UUID,
    user_id: UUID | None,
) -> str:
    owner = str(user_id) if user_id is not None else "anonymous"
    return f"{project_id}:{owner}"


def _chat_rate_key(*, project_id: UUID, user_id: UUID | None) -> str:
    return _chat_user_flight_key(project_id=project_id, user_id=user_id)


def _try_acquire_chat_flight(flight_key: str | None) -> bool:
    if flight_key is None:
        return True
    with _CHAT_FLIGHT_LOCK:
        if flight_key in _CHAT_IN_FLIGHT:
            return False
        _CHAT_IN_FLIGHT.add(flight_key)
        return True


def _release_chat_flight(flight_key: str | None) -> None:
    if flight_key is None:
        return
    with _CHAT_FLIGHT_LOCK:
        _CHAT_IN_FLIGHT.discard(flight_key)


def _try_acquire_chat_user_flight(user_flight_key: str) -> bool:
    """At most one concurrent stream per (project, user)."""

    with _CHAT_FLIGHT_LOCK:
        if user_flight_key in _CHAT_USER_IN_FLIGHT:
            return False
        _CHAT_USER_IN_FLIGHT.add(user_flight_key)
        return True


def _release_chat_user_flight(user_flight_key: str | None) -> None:
    if user_flight_key is None:
        return
    with _CHAT_FLIGHT_LOCK:
        _CHAT_USER_IN_FLIGHT.discard(user_flight_key)


def _try_acquire_chat_rate(rate_key: str) -> bool:
    now = time.monotonic()
    window_start = now - 60.0
    with _CHAT_FLIGHT_LOCK:
        bucket = _CHAT_RATE_WINDOWS[rate_key]
        while bucket and bucket[0] < window_start:
            bucket.popleft()
        if len(bucket) >= _CHAT_RATE_LIMIT_PER_MINUTE:
            return False
        bucket.append(now)
        return True


def _commit_or_rollback_chat_error(session: Session) -> None:
    try:
        session.commit()
    except Exception as exc:
        logger.warning(
            "chat_error_audit_commit_failed; rolling back",
            extra={"error_type": type(exc).__name__},
            exc_info=exc,
        )
        session.rollback()


def _history_user_id(current: CurrentPrincipal) -> UUID | None:
    return None if current.is_superadmin else current.user_id


def _with_approved_user_memory(
    session: Session,
    *,
    request: ChatRequest,
    user_id: UUID | None,
    project_id: UUID,
) -> ChatRequest:
    """Attach approved durable memories as runner system context (not audit text)."""

    if user_id is None:
        return request
    from adaptive_rag.user_memory import approved_injection_text

    injection = approved_injection_text(
        session,
        user_id=user_id,
        project_id=project_id,
    )
    if not injection:
        return request
    # Keep request.message as the raw user turn for audit/history/condenser.
    return replace(request, user_memory=injection)
