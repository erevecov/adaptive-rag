"""HTTP routes for global runtime slot defaults and chat model pool."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from adaptive_rag.api.dependencies import get_session
from adaptive_rag.api.schemas.runtime_settings import (
    ChatModelListResponse,
    ChatModelResponse,
    ChatModelUpsertRequestBody,
    DeleteResponse,
    RuntimeSlotDefaultListResponse,
    RuntimeSlotDefaultResponse,
    RuntimeSlotDefaultUpsertRequestBody,
)
from adaptive_rag.db.repositories import RuntimeSettingsRepository

router = APIRouter(prefix="/runtime-settings", tags=["runtime-settings"])


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


def _http_error(error: ValueError) -> HTTPException:
    message = str(error)
    code = message.split(":", maxsplit=1)[0]
    if code == "connection_not_found" or code == "chat_model_not_found":
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
