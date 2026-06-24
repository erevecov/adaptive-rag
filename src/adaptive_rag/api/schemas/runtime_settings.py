"""Schemas HTTP for global runtime slot defaults and chat model pool."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from adaptive_rag.db.models import GlobalChatModel, RuntimeSlotDefault


class RuntimeSlotDefaultUpsertRequestBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    connection_id: str
    model_id: str
    parameters: dict[str, Any] | None = None


class RuntimeSlotDefaultResponse(BaseModel):
    slot: str
    connection_id: str
    model_id: str
    parameters: dict[str, Any] | None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_default(
        cls,
        default: RuntimeSlotDefault,
    ) -> RuntimeSlotDefaultResponse:
        return cls(
            slot=default.slot,
            connection_id=default.connection_id,
            model_id=default.model_id,
            parameters=default.parameters_json,
            created_at=default.created_at,
            updated_at=default.updated_at,
        )


class RuntimeSlotDefaultListResponse(BaseModel):
    items: list[RuntimeSlotDefaultResponse]


class ChatModelUpsertRequestBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    connection_id: str
    model_id: str
    make_default: bool = False
    parameters: dict[str, Any] | None = None


class ChatModelResponse(BaseModel):
    connection_id: str
    model_id: str
    is_default: bool
    parameters: dict[str, Any] | None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_model(cls, model: GlobalChatModel) -> ChatModelResponse:
        return cls(
            connection_id=model.connection_id,
            model_id=model.model_id,
            is_default=model.is_default,
            parameters=model.parameters_json,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )


class ChatModelListResponse(BaseModel):
    items: list[ChatModelResponse]


class DeleteResponse(BaseModel):
    deleted: bool = Field()
