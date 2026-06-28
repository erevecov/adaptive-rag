"""HTTP routes for global runtime slot defaults and chat model pool."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from adaptive_rag.api.dependencies import (
    get_current_user,
    get_session,
    get_superadmin_user,
)
from adaptive_rag.api.schemas.runtime_settings import (
    ChatModelListResponse,
    ChatModelResponse,
    ChatModelUpsertRequestBody,
    ChatRetrievalSettingsRequestBody,
    DeleteResponse,
    GlobalChatRetrievalSettingsResponse,
    ProjectChatModelResponse,
    ProjectChatRetrievalSettingsResponse,
    ProjectRuntimeSettingsResponse,
    ProjectRuntimeSlotResponse,
    RuntimeSlotDefaultListResponse,
    RuntimeSlotDefaultResponse,
    RuntimeSlotDefaultUpsertRequestBody,
)
from adaptive_rag.auth import CurrentPrincipal, get_project_role, role_meets
from adaptive_rag.db.models import Project
from adaptive_rag.db.repositories import (
    ChatRetrievalSettingsRepository,
    ProjectRuntimeSettingsRepository,
    RuntimeSettingsRepository,
)


def _require_project_runtime_admin_access(
    project_id: UUID,
    session: Annotated[Session, Depends(get_session)],
    current: Annotated[CurrentPrincipal, Depends(get_current_user)],
) -> tuple[Project, str]:
    project = session.get(Project, project_id)
    if project is None:
        raise HTTPException(
            status_code=404,
            detail={"code": "project_not_found", "message": "project_not_found"},
        )
    role = get_project_role(session, principal=current, project_id=project_id)
    if role is None:
        raise HTTPException(status_code=403, detail="project access required")
    if not role_meets(role, "admin"):
        raise HTTPException(status_code=403, detail="project admin role required")
    return project, role


router = APIRouter(
    prefix="/runtime-settings",
    tags=["runtime-settings"],
    dependencies=[Depends(get_superadmin_user)],
)
project_router = APIRouter(
    tags=["runtime-settings"],
    dependencies=[Depends(_require_project_runtime_admin_access)],
)


@router.get("/slots", response_model=RuntimeSlotDefaultListResponse)
def list_runtime_slot_defaults(
    session: Annotated[Session, Depends(get_session)],
) -> RuntimeSlotDefaultListResponse:
    defaults = RuntimeSettingsRepository(session).list_slot_defaults()
    return RuntimeSlotDefaultListResponse(
        items=[RuntimeSlotDefaultResponse.from_default(default) for default in defaults]
    )


@router.put("/slots/{slot}", response_model=RuntimeSlotDefaultResponse)
def upsert_runtime_slot_default(
    slot: str,
    body: RuntimeSlotDefaultUpsertRequestBody,
    session: Annotated[Session, Depends(get_session)],
) -> RuntimeSlotDefaultResponse:
    try:
        default = RuntimeSettingsRepository(session).upsert_slot_default(
            slot=slot,
            connection_id=body.connection_id,
            model_id=body.model_id,
            parameters=body.parameters,
        )
    except ValueError as exc:
        raise _http_error(exc) from exc
    session.commit()
    return RuntimeSlotDefaultResponse.from_default(default)


@router.delete("/slots/{slot}", response_model=DeleteResponse)
def delete_runtime_slot_default(
    slot: str,
    session: Annotated[Session, Depends(get_session)],
) -> DeleteResponse:
    try:
        deleted = RuntimeSettingsRepository(session).delete_slot_default(slot)
    except ValueError as exc:
        raise _http_error(exc) from exc
    session.commit()
    return DeleteResponse(deleted=deleted)


@router.get("/chat/models", response_model=ChatModelListResponse)
def list_chat_models(
    session: Annotated[Session, Depends(get_session)],
) -> ChatModelListResponse:
    models = RuntimeSettingsRepository(session).list_chat_models()
    return ChatModelListResponse(
        items=[ChatModelResponse.from_model(model) for model in models]
    )


@router.post("/chat/models", response_model=ChatModelResponse)
def upsert_chat_model(
    body: ChatModelUpsertRequestBody,
    session: Annotated[Session, Depends(get_session)],
) -> ChatModelResponse:
    try:
        model = RuntimeSettingsRepository(session).upsert_chat_model(
            connection_id=body.connection_id,
            model_id=body.model_id,
            make_default=body.make_default,
            parameters=body.parameters,
        )
    except ValueError as exc:
        raise _http_error(exc) from exc
    session.commit()
    return ChatModelResponse.from_model(model)


@router.put(
    "/chat/models/{connection_id}/{model_id}/default",
    response_model=ChatModelResponse,
)
def set_default_chat_model(
    connection_id: str,
    model_id: str,
    session: Annotated[Session, Depends(get_session)],
) -> ChatModelResponse:
    try:
        model = RuntimeSettingsRepository(session).set_default_chat_model(
            connection_id=connection_id,
            model_id=model_id,
        )
    except ValueError as exc:
        raise _http_error(exc) from exc
    session.commit()
    return ChatModelResponse.from_model(model)


@router.delete("/chat/models/{connection_id}/{model_id}", response_model=DeleteResponse)
def delete_chat_model(
    connection_id: str,
    model_id: str,
    session: Annotated[Session, Depends(get_session)],
) -> DeleteResponse:
    try:
        deleted = RuntimeSettingsRepository(session).delete_chat_model(
            connection_id=connection_id,
            model_id=model_id,
        )
    except ValueError as exc:
        raise _http_error(exc) from exc
    session.commit()
    return DeleteResponse(deleted=deleted)


@router.get(
    "/chat/retrieval",
    response_model=GlobalChatRetrievalSettingsResponse,
)
def get_chat_retrieval_settings(
    session: Annotated[Session, Depends(get_session)],
) -> GlobalChatRetrievalSettingsResponse:
    settings = ChatRetrievalSettingsRepository(session).get_global_settings()
    return GlobalChatRetrievalSettingsResponse.from_model(settings)


@router.put(
    "/chat/retrieval",
    response_model=GlobalChatRetrievalSettingsResponse,
)
def update_chat_retrieval_settings(
    body: ChatRetrievalSettingsRequestBody,
    session: Annotated[Session, Depends(get_session)],
) -> GlobalChatRetrievalSettingsResponse:
    try:
        settings = ChatRetrievalSettingsRepository(session).upsert_global_settings(
            retrieval_limit=body.retrieval_limit,
            rerank_enabled=body.rerank_enabled,
            rerank_candidate_limit=body.rerank_candidate_limit,
        )
    except ValueError as exc:
        raise _http_error(exc) from exc
    session.commit()
    return GlobalChatRetrievalSettingsResponse.from_model(settings)


@project_router.get(
    "/projects/{project_id}/runtime-settings",
    response_model=ProjectRuntimeSettingsResponse,
)
def get_project_runtime_settings(
    project_id: UUID,
    session: Annotated[Session, Depends(get_session)],
) -> ProjectRuntimeSettingsResponse:
    try:
        settings = ProjectRuntimeSettingsRepository(
            session
        ).get_project_runtime_settings(project_id)
    except ValueError as exc:
        raise _http_error(exc) from exc
    return ProjectRuntimeSettingsResponse.from_settings(settings)


@project_router.put(
    "/projects/{project_id}/runtime-settings/chat/retrieval",
    response_model=ProjectChatRetrievalSettingsResponse,
)
def update_project_chat_retrieval_settings(
    project_id: UUID,
    body: ChatRetrievalSettingsRequestBody,
    session: Annotated[Session, Depends(get_session)],
) -> ProjectChatRetrievalSettingsResponse:
    try:
        settings = ChatRetrievalSettingsRepository(session).upsert_project_settings(
            project_id=project_id,
            retrieval_limit=body.retrieval_limit,
            rerank_enabled=body.rerank_enabled,
            rerank_candidate_limit=body.rerank_candidate_limit,
        )
    except ValueError as exc:
        raise _http_error(exc) from exc
    session.commit()
    return ProjectChatRetrievalSettingsResponse.from_model(settings)


@project_router.delete(
    "/projects/{project_id}/runtime-settings/chat/retrieval",
    response_model=DeleteResponse,
)
def delete_project_chat_retrieval_settings(
    project_id: UUID,
    session: Annotated[Session, Depends(get_session)],
) -> DeleteResponse:
    try:
        deleted = ChatRetrievalSettingsRepository(session).delete_project_settings(
            project_id=project_id,
        )
    except ValueError as exc:
        raise _http_error(exc) from exc
    session.commit()
    return DeleteResponse(deleted=deleted)


@project_router.put(
    "/projects/{project_id}/runtime-settings/slots/{slot}",
    response_model=ProjectRuntimeSlotResponse,
)
def upsert_project_runtime_slot_override(
    project_id: UUID,
    slot: str,
    body: RuntimeSlotDefaultUpsertRequestBody,
    session: Annotated[Session, Depends(get_session)],
) -> ProjectRuntimeSlotResponse:
    try:
        override = ProjectRuntimeSettingsRepository(session).upsert_slot_override(
            project_id=project_id,
            slot=slot,
            connection_id=body.connection_id,
            model_id=body.model_id,
            parameters=body.parameters,
        )
    except ValueError as exc:
        raise _http_error(exc) from exc
    session.commit()
    return ProjectRuntimeSlotResponse.from_override(override)


@project_router.delete(
    "/projects/{project_id}/runtime-settings/slots/{slot}",
    response_model=DeleteResponse,
)
def delete_project_runtime_slot_override(
    project_id: UUID,
    slot: str,
    session: Annotated[Session, Depends(get_session)],
) -> DeleteResponse:
    try:
        deleted = ProjectRuntimeSettingsRepository(session).delete_slot_override(
            project_id=project_id,
            slot=slot,
        )
    except ValueError as exc:
        raise _http_error(exc) from exc
    session.commit()
    return DeleteResponse(deleted=deleted)


@project_router.put(
    "/projects/{project_id}/runtime-settings/chat/models",
    response_model=ProjectChatModelResponse,
)
def upsert_project_chat_model(
    project_id: UUID,
    body: ChatModelUpsertRequestBody,
    session: Annotated[Session, Depends(get_session)],
) -> ProjectChatModelResponse:
    try:
        model = ProjectRuntimeSettingsRepository(session).upsert_chat_model(
            project_id=project_id,
            connection_id=body.connection_id,
            model_id=body.model_id,
            make_default=body.make_default,
            parameters=body.parameters,
        )
    except ValueError as exc:
        raise _http_error(exc) from exc
    session.commit()
    return ProjectChatModelResponse.from_model(model)


@project_router.put(
    "/projects/{project_id}/runtime-settings/chat/models/{connection_id}/"
    "{model_id}/default",
    response_model=ProjectChatModelResponse,
)
def set_default_project_chat_model(
    project_id: UUID,
    connection_id: str,
    model_id: str,
    session: Annotated[Session, Depends(get_session)],
) -> ProjectChatModelResponse:
    try:
        model = ProjectRuntimeSettingsRepository(session).set_default_chat_model(
            project_id=project_id,
            connection_id=connection_id,
            model_id=model_id,
        )
    except ValueError as exc:
        raise _http_error(exc) from exc
    session.commit()
    return ProjectChatModelResponse.from_model(model)


@project_router.delete(
    "/projects/{project_id}/runtime-settings/chat/models/{connection_id}/{model_id}",
    response_model=DeleteResponse,
)
def delete_project_chat_model(
    project_id: UUID,
    connection_id: str,
    model_id: str,
    session: Annotated[Session, Depends(get_session)],
) -> DeleteResponse:
    try:
        deleted = ProjectRuntimeSettingsRepository(session).delete_chat_model(
            project_id=project_id,
            connection_id=connection_id,
            model_id=model_id,
        )
    except ValueError as exc:
        raise _http_error(exc) from exc
    session.commit()
    return DeleteResponse(deleted=deleted)


def _http_error(error: ValueError) -> HTTPException:
    message = str(error)
    code = message.split(":", maxsplit=1)[0]
    if code in {"connection_not_found", "chat_model_not_found", "project_not_found"}:
        return HTTPException(
            status_code=404,
            detail={"code": code, "message": message},
        )
    if code in {"cannot_delete_last_chat_model", "cannot_delete_default_chat_model"}:
        return HTTPException(
            status_code=409,
            detail={"code": code, "message": message},
        )
    if code in {"unsupported_slot", "connection_unavailable"}:
        return HTTPException(
            status_code=422,
            detail={"code": code, "message": message},
        )
    return HTTPException(
        status_code=422,
        detail={"code": "invalid_runtime_settings", "message": message},
    )
