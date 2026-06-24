"""Schemas HTTP for global runtime slot defaults and chat model pool."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from adaptive_rag.db.models import (
    GlobalChatModel,
    ProjectChatModel,
    ProjectRuntimeSlotOverride,
    RuntimeSlotDefault,
)
from adaptive_rag.db.repositories import (
    EffectiveChatModel,
    EffectiveRuntimeSlot,
    ProjectRuntimeSettings,
)


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


class ProjectRuntimeSlotResponse(BaseModel):
    slot: str
    source: str
    connection_id: str
    model_id: str
    parameters: dict[str, Any] | None

    @classmethod
    def from_effective(
        cls,
        slot: EffectiveRuntimeSlot,
    ) -> ProjectRuntimeSlotResponse:
        return cls(
            slot=slot.slot,
            source=slot.source,
            connection_id=slot.connection_id,
            model_id=slot.model_id,
            parameters=slot.parameters_json,
        )

    @classmethod
    def from_override(
        cls,
        override: ProjectRuntimeSlotOverride,
    ) -> ProjectRuntimeSlotResponse:
        return cls(
            slot=override.slot,
            source="overridden",
            connection_id=override.connection_id,
            model_id=override.model_id,
            parameters=override.parameters_json,
        )


class ProjectChatModelResponse(BaseModel):
    connection_id: str
    model_id: str
    is_default: bool
    source: str
    parameters: dict[str, Any] | None

    @classmethod
    def from_effective(cls, model: EffectiveChatModel) -> ProjectChatModelResponse:
        return cls(
            connection_id=model.connection_id,
            model_id=model.model_id,
            is_default=model.is_default,
            source=model.source,
            parameters=model.parameters_json,
        )

    @classmethod
    def from_model(cls, model: ProjectChatModel) -> ProjectChatModelResponse:
        return cls(
            connection_id=model.connection_id,
            model_id=model.model_id,
            is_default=model.is_default,
            source="overridden",
            parameters=model.parameters_json,
        )


class ProjectRuntimeSettingsResponse(BaseModel):
    project_id: UUID
    slots: list[ProjectRuntimeSlotResponse]
    chat_models: list[ProjectChatModelResponse]

    @classmethod
    def from_settings(
        cls,
        settings: ProjectRuntimeSettings,
    ) -> ProjectRuntimeSettingsResponse:
        return cls(
            project_id=settings.project_id,
            slots=[
                ProjectRuntimeSlotResponse.from_effective(slot)
                for slot in settings.slots
            ],
            chat_models=[
                ProjectChatModelResponse.from_effective(model)
                for model in settings.chat_models
            ],
        )
