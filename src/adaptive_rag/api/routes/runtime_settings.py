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
    RuntimeSlotDefaultListResponse,
    RuntimeSlotDefaultResponse,
    RuntimeSlotDefaultUpsertRequestBody,
    WorkspaceChatModelResponse,
    WorkspaceChatRetrievalSettingsResponse,
    WorkspaceRuntimeSettingsResponse,
    WorkspaceRuntimeSlotResponse,
)
from adaptive_rag.auth import CurrentPrincipal, get_workspace_role, role_meets
from adaptive_rag.db.models import Workspace
from adaptive_rag.db.repositories import (
    ChatRetrievalSettingsRepository,
    RuntimeSettingsRepository,
    WorkspaceRepository,
    WorkspaceRuntimeSettingsRepository,
)


def _require_workspace_runtime_admin_access(
    workspace_id: UUID,
    session: Annotated[Session, Depends(get_session)],
    current: Annotated[CurrentPrincipal, Depends(get_current_user)],
) -> tuple[Workspace, str]:
    # Soft-deleted workspaces are not found (same contract as get_workspace_access).
    workspace = WorkspaceRepository(session).get(workspace_id)
    if workspace is None:
        raise HTTPException(
            status_code=404,
            detail={"code": "workspace_not_found", "message": "workspace_not_found"},
        )
    role = get_workspace_role(session, principal=current, workspace_id=workspace_id)
    if role is None:
        raise HTTPException(status_code=403, detail="workspace access required")
    if not role_meets(role, "admin"):
        raise HTTPException(status_code=403, detail="workspace admin role required")
    return workspace, role


router = APIRouter(
    prefix="/runtime-settings",
    tags=["runtime-settings"],
    dependencies=[Depends(get_superadmin_user)],
)
workspace_router = APIRouter(
    tags=["runtime-settings"],
    dependencies=[Depends(_require_workspace_runtime_admin_access)],
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


@workspace_router.get(
    "/workspaces/{workspace_id}/runtime-settings",
    response_model=WorkspaceRuntimeSettingsResponse,
)
def get_workspace_runtime_settings(
    workspace_id: UUID,
    session: Annotated[Session, Depends(get_session)],
) -> WorkspaceRuntimeSettingsResponse:
    try:
        settings = WorkspaceRuntimeSettingsRepository(
            session
        ).get_workspace_runtime_settings(workspace_id)
    except ValueError as exc:
        raise _http_error(exc) from exc
    return WorkspaceRuntimeSettingsResponse.from_settings(settings)


@workspace_router.put(
    "/workspaces/{workspace_id}/runtime-settings/chat/retrieval",
    response_model=WorkspaceChatRetrievalSettingsResponse,
)
def update_workspace_chat_retrieval_settings(
    workspace_id: UUID,
    body: ChatRetrievalSettingsRequestBody,
    session: Annotated[Session, Depends(get_session)],
) -> WorkspaceChatRetrievalSettingsResponse:
    try:
        settings = ChatRetrievalSettingsRepository(session).upsert_workspace_settings(
            workspace_id=workspace_id,
            retrieval_limit=body.retrieval_limit,
            rerank_enabled=body.rerank_enabled,
            rerank_candidate_limit=body.rerank_candidate_limit,
        )
    except ValueError as exc:
        raise _http_error(exc) from exc
    session.commit()
    return WorkspaceChatRetrievalSettingsResponse.from_model(settings)


@workspace_router.delete(
    "/workspaces/{workspace_id}/runtime-settings/chat/retrieval",
    response_model=DeleteResponse,
)
def delete_workspace_chat_retrieval_settings(
    workspace_id: UUID,
    session: Annotated[Session, Depends(get_session)],
) -> DeleteResponse:
    try:
        deleted = ChatRetrievalSettingsRepository(session).delete_workspace_settings(
            workspace_id=workspace_id,
        )
    except ValueError as exc:
        raise _http_error(exc) from exc
    session.commit()
    return DeleteResponse(deleted=deleted)


@workspace_router.put(
    "/workspaces/{workspace_id}/runtime-settings/slots/{slot}",
    response_model=WorkspaceRuntimeSlotResponse,
)
def upsert_workspace_runtime_slot_override(
    workspace_id: UUID,
    slot: str,
    body: RuntimeSlotDefaultUpsertRequestBody,
    session: Annotated[Session, Depends(get_session)],
) -> WorkspaceRuntimeSlotResponse:
    try:
        override = WorkspaceRuntimeSettingsRepository(session).upsert_slot_override(
            workspace_id=workspace_id,
            slot=slot,
            connection_id=body.connection_id,
            model_id=body.model_id,
            parameters=body.parameters,
        )
    except ValueError as exc:
        raise _http_error(exc) from exc
    session.commit()
    return WorkspaceRuntimeSlotResponse.from_override(override)


@workspace_router.delete(
    "/workspaces/{workspace_id}/runtime-settings/slots/{slot}",
    response_model=DeleteResponse,
)
def delete_workspace_runtime_slot_override(
    workspace_id: UUID,
    slot: str,
    session: Annotated[Session, Depends(get_session)],
) -> DeleteResponse:
    try:
        deleted = WorkspaceRuntimeSettingsRepository(session).delete_slot_override(
            workspace_id=workspace_id,
            slot=slot,
        )
    except ValueError as exc:
        raise _http_error(exc) from exc
    session.commit()
    return DeleteResponse(deleted=deleted)


@workspace_router.put(
    "/workspaces/{workspace_id}/runtime-settings/chat/models",
    response_model=WorkspaceChatModelResponse,
)
def upsert_workspace_chat_model(
    workspace_id: UUID,
    body: ChatModelUpsertRequestBody,
    session: Annotated[Session, Depends(get_session)],
) -> WorkspaceChatModelResponse:
    try:
        model = WorkspaceRuntimeSettingsRepository(session).upsert_chat_model(
            workspace_id=workspace_id,
            connection_id=body.connection_id,
            model_id=body.model_id,
            make_default=body.make_default,
            parameters=body.parameters,
        )
    except ValueError as exc:
        raise _http_error(exc) from exc
    session.commit()
    return WorkspaceChatModelResponse.from_model(model)


@workspace_router.put(
    "/workspaces/{workspace_id}/runtime-settings/chat/models/{connection_id}/"
    "{model_id}/default",
    response_model=WorkspaceChatModelResponse,
)
def set_default_workspace_chat_model(
    workspace_id: UUID,
    connection_id: str,
    model_id: str,
    session: Annotated[Session, Depends(get_session)],
) -> WorkspaceChatModelResponse:
    try:
        model = WorkspaceRuntimeSettingsRepository(session).set_default_chat_model(
            workspace_id=workspace_id,
            connection_id=connection_id,
            model_id=model_id,
        )
    except ValueError as exc:
        raise _http_error(exc) from exc
    session.commit()
    return WorkspaceChatModelResponse.from_model(model)


@workspace_router.delete(
    "/workspaces/{workspace_id}/runtime-settings/chat/models/{connection_id}/{model_id}",
    response_model=DeleteResponse,
)
def delete_workspace_chat_model(
    workspace_id: UUID,
    connection_id: str,
    model_id: str,
    session: Annotated[Session, Depends(get_session)],
) -> DeleteResponse:
    try:
        deleted = WorkspaceRuntimeSettingsRepository(session).delete_chat_model(
            workspace_id=workspace_id,
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
    if code in {"connection_not_found", "chat_model_not_found", "workspace_not_found"}:
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
