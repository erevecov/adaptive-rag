"""Schemas HTTP for global runtime slot defaults and chat model pool."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from adaptive_rag.db.models import (
    GlobalChatModel,
    GlobalChatRetrievalSettings,
    RuntimeSlotDefault,
    WorkspaceChatModel,
    WorkspaceChatRetrievalSettings,
    WorkspaceRuntimeSlotOverride,
)
from adaptive_rag.db.repositories import (
    EffectiveChatModel,
    EffectiveChatRetrievalSettings,
    EffectiveRuntimeSlot,
    WorkspaceRuntimeSettings,
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


class ChatRetrievalSettingsRequestBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    retrieval_limit: int
    rerank_enabled: bool
    rerank_candidate_limit: int


class GlobalChatRetrievalSettingsResponse(BaseModel):
    retrieval_limit: int
    rerank_enabled: bool
    rerank_candidate_limit: int
    max_limit: int

    @classmethod
    def from_model(
        cls,
        settings: GlobalChatRetrievalSettings,
    ) -> GlobalChatRetrievalSettingsResponse:
        return cls(
            retrieval_limit=settings.retrieval_limit,
            rerank_enabled=settings.rerank_enabled,
            rerank_candidate_limit=settings.rerank_candidate_limit,
            max_limit=settings.max_limit,
        )


class WorkspaceChatRetrievalSettingsResponse(BaseModel):
    source: str
    retrieval_limit: int
    rerank_enabled: bool
    rerank_candidate_limit: int
    max_limit: int

    @classmethod
    def from_effective(
        cls,
        settings: EffectiveChatRetrievalSettings,
    ) -> WorkspaceChatRetrievalSettingsResponse:
        return cls(
            source=settings.source,
            retrieval_limit=settings.retrieval_limit,
            rerank_enabled=settings.rerank_enabled,
            rerank_candidate_limit=settings.rerank_candidate_limit,
            max_limit=settings.max_limit,
        )

    @classmethod
    def from_model(
        cls,
        settings: WorkspaceChatRetrievalSettings,
    ) -> WorkspaceChatRetrievalSettingsResponse:
        return cls(
            source="workspace",
            retrieval_limit=settings.retrieval_limit,
            rerank_enabled=settings.rerank_enabled,
            rerank_candidate_limit=settings.rerank_candidate_limit,
            max_limit=50,
        )


class DeleteResponse(BaseModel):
    deleted: bool = Field()


class WorkspaceRuntimeSlotResponse(BaseModel):
    slot: str
    source: str
    connection_id: str
    model_id: str
    parameters: dict[str, Any] | None

    @classmethod
    def from_effective(
        cls,
        slot: EffectiveRuntimeSlot,
    ) -> WorkspaceRuntimeSlotResponse:
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
        override: WorkspaceRuntimeSlotOverride,
    ) -> WorkspaceRuntimeSlotResponse:
        return cls(
            slot=override.slot,
            source="overridden",
            connection_id=override.connection_id,
            model_id=override.model_id,
            parameters=override.parameters_json,
        )


class WorkspaceChatModelResponse(BaseModel):
    connection_id: str
    model_id: str
    is_default: bool
    source: str
    parameters: dict[str, Any] | None

    @classmethod
    def from_effective(cls, model: EffectiveChatModel) -> WorkspaceChatModelResponse:
        return cls(
            connection_id=model.connection_id,
            model_id=model.model_id,
            is_default=model.is_default,
            source=model.source,
            parameters=model.parameters_json,
        )

    @classmethod
    def from_model(cls, model: WorkspaceChatModel) -> WorkspaceChatModelResponse:
        return cls(
            connection_id=model.connection_id,
            model_id=model.model_id,
            is_default=model.is_default,
            source="overridden",
            parameters=model.parameters_json,
        )


class WorkspaceRuntimeSettingsResponse(BaseModel):
    workspace_id: UUID
    slots: list[WorkspaceRuntimeSlotResponse]
    chat_models: list[WorkspaceChatModelResponse]
    chat_retrieval: WorkspaceChatRetrievalSettingsResponse

    @classmethod
    def from_settings(
        cls,
        settings: WorkspaceRuntimeSettings,
    ) -> WorkspaceRuntimeSettingsResponse:
        return cls(
            workspace_id=settings.workspace_id,
            slots=[
                WorkspaceRuntimeSlotResponse.from_effective(slot)
                for slot in settings.slots
            ],
            chat_models=[
                WorkspaceChatModelResponse.from_effective(model)
                for model in settings.chat_models
            ],
            chat_retrieval=WorkspaceChatRetrievalSettingsResponse.from_effective(
                settings.chat_retrieval
            ),
        )
