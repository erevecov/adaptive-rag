"""Repository for global runtime slot defaults and chat model pool."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from adaptive_rag.db.models import (
    CHAT_RETRIEVAL_MAX_LIMIT,
    DEFAULT_CHAT_RERANK_CANDIDATE_LIMIT,
    DEFAULT_CHAT_RERANK_ENABLED,
    DEFAULT_CHAT_RETRIEVAL_LIMIT,
    RUNTIME_SLOT_VALUES,
    GlobalChatModel,
    GlobalChatRetrievalSettings,
    Project,
    ProjectChatModel,
    ProjectChatRetrievalSettings,
    ProjectRuntimeSlotOverride,
    ProviderConnection,
    RuntimeSlotDefault,
)


@dataclass(frozen=True)
class EffectiveRuntimeSlot:
    """Effective project runtime slot value with inheritance metadata."""

    slot: str
    source: str
    connection_id: str
    model_id: str
    parameters_json: dict[str, Any] | None


@dataclass(frozen=True)
class EffectiveChatModel:
    """Effective project chat model pool entry with inheritance metadata."""

    connection_id: str
    model_id: str
    is_default: bool
    source: str
    parameters_json: dict[str, Any] | None


@dataclass(frozen=True)
class ProjectRuntimeSettings:
    """Effective runtime settings for one project."""

    project_id: UUID
    slots: list[EffectiveRuntimeSlot]
    chat_models: list[EffectiveChatModel]
    chat_retrieval: EffectiveChatRetrievalSettings


@dataclass(frozen=True)
class EffectiveChatRetrievalSettings:
    """Effective chat retrieval behavior with inheritance metadata."""

    source: str
    retrieval_limit: int
    rerank_enabled: bool
    rerank_candidate_limit: int
    max_limit: int = CHAT_RETRIEVAL_MAX_LIMIT


class ChatRetrievalSettingsRepository:
    """Persistence for chat retrieval defaults and project overrides."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get_global_settings(self) -> GlobalChatRetrievalSettings:
        settings = self._session.get(GlobalChatRetrievalSettings, 1)
        if settings is None:
            settings = GlobalChatRetrievalSettings(
                id=1,
                retrieval_limit=DEFAULT_CHAT_RETRIEVAL_LIMIT,
                rerank_enabled=DEFAULT_CHAT_RERANK_ENABLED,
                rerank_candidate_limit=DEFAULT_CHAT_RERANK_CANDIDATE_LIMIT,
                max_limit=CHAT_RETRIEVAL_MAX_LIMIT,
            )
            self._session.add(settings)
            self._session.flush()
        return settings

    def upsert_global_settings(
        self,
        *,
        retrieval_limit: int,
        rerank_enabled: bool,
        rerank_candidate_limit: int,
    ) -> GlobalChatRetrievalSettings:
        _validate_chat_retrieval_settings(
            retrieval_limit=retrieval_limit,
            rerank_enabled=rerank_enabled,
            rerank_candidate_limit=rerank_candidate_limit,
        )
        settings = self.get_global_settings()
        settings.retrieval_limit = retrieval_limit
        settings.rerank_enabled = rerank_enabled
        settings.rerank_candidate_limit = rerank_candidate_limit
        settings.max_limit = CHAT_RETRIEVAL_MAX_LIMIT
        self._session.flush()
        return settings

    def get_project_settings(
        self,
        project_id: UUID,
    ) -> ProjectChatRetrievalSettings | None:
        return self._session.get(ProjectChatRetrievalSettings, project_id)

    def get_effective_project_settings(
        self,
        project_id: UUID,
    ) -> EffectiveChatRetrievalSettings:
        project = self._require_project(project_id)
        override = self.get_project_settings(project.id)
        if override is not None:
            return EffectiveChatRetrievalSettings(
                source="project",
                retrieval_limit=override.retrieval_limit,
                rerank_enabled=override.rerank_enabled,
                rerank_candidate_limit=override.rerank_candidate_limit,
            )
        global_settings = self.get_global_settings()
        return EffectiveChatRetrievalSettings(
            source="global",
            retrieval_limit=global_settings.retrieval_limit,
            rerank_enabled=global_settings.rerank_enabled,
            rerank_candidate_limit=global_settings.rerank_candidate_limit,
            max_limit=global_settings.max_limit,
        )

    def upsert_project_settings(
        self,
        *,
        project_id: UUID,
        retrieval_limit: int,
        rerank_enabled: bool,
        rerank_candidate_limit: int,
    ) -> ProjectChatRetrievalSettings:
        project = self._require_project(project_id)
        _validate_chat_retrieval_settings(
            retrieval_limit=retrieval_limit,
            rerank_enabled=rerank_enabled,
            rerank_candidate_limit=rerank_candidate_limit,
        )
        settings = self.get_project_settings(project.id)
        if settings is None:
            settings = ProjectChatRetrievalSettings(
                project_id=project.id,
                retrieval_limit=retrieval_limit,
                rerank_enabled=rerank_enabled,
                rerank_candidate_limit=rerank_candidate_limit,
            )
            self._session.add(settings)
        else:
            settings.retrieval_limit = retrieval_limit
            settings.rerank_enabled = rerank_enabled
            settings.rerank_candidate_limit = rerank_candidate_limit
        self._session.flush()
        return settings

    def delete_project_settings(self, *, project_id: UUID) -> bool:
        project = self._require_project(project_id)
        settings = self.get_project_settings(project.id)
        if settings is None:
            return False
        self._session.delete(settings)
        self._session.flush()
        return True

    def _require_project(self, project_id: UUID) -> Project:
        project = self._session.get(Project, project_id)
        if project is None:
            raise ValueError("project_not_found")
        return project


class RuntimeSettingsRepository:
    """Persistence for global runtime defaults.

    Transactions are controlled by the caller. Repository methods flush but do
    not commit.
    """

    def __init__(self, session: Session) -> None:
        self._session = session

    def upsert_slot_default(
        self,
        *,
        slot: str,
        connection_id: str,
        model_id: str,
        parameters: Mapping[str, Any] | None = None,
    ) -> RuntimeSlotDefault:
        slot = _normalize_slot(slot)
        model_id = _normalize_model_id(model_id)
        connection = self._require_connection(connection_id)
        _require_capability(connection, slot)
        parameters_json = dict(parameters) if parameters is not None else None

        default = self._upsert_slot_default_row(
            slot=slot,
            connection_id=connection.connection_id,
            model_id=model_id,
            parameters=parameters_json,
        )

        if slot == "chat":
            self.upsert_chat_model(
                connection_id=connection.connection_id,
                model_id=model_id,
                make_default=True,
                parameters=parameters_json,
                sync_slot_default=False,
            )

        self._session.flush()
        return default

    def get_slot_default(self, slot: str) -> RuntimeSlotDefault | None:
        return self._session.get(RuntimeSlotDefault, slot)

    def list_slot_defaults(self) -> list[RuntimeSlotDefault]:
        statement = select(RuntimeSlotDefault).order_by(RuntimeSlotDefault.slot)
        return list(self._session.scalars(statement))

    def delete_slot_default(self, slot: str) -> bool:
        slot = _normalize_slot(slot)
        default = self.get_slot_default(slot)
        if default is None:
            return False
        self._session.delete(default)
        self._session.flush()
        return True

    def upsert_chat_model(
        self,
        *,
        connection_id: str,
        model_id: str,
        make_default: bool = False,
        parameters: Mapping[str, Any] | None = None,
        sync_slot_default: bool = True,
    ) -> GlobalChatModel:
        model_id = _normalize_model_id(model_id)
        connection = self._require_connection(connection_id)
        _require_capability(connection, "chat")
        parameters_json = dict(parameters) if parameters is not None else None
        should_be_default = make_default or len(self.list_chat_models()) == 0

        if should_be_default:
            self._clear_chat_defaults()

        model = self._get_chat_model(connection.connection_id, model_id)
        if model is None:
            model = GlobalChatModel(
                connection_id=connection.connection_id,
                model_id=model_id,
                is_default=should_be_default,
                parameters_json=parameters_json,
            )
            self._session.add(model)
        else:
            model.parameters_json = parameters_json
            if should_be_default:
                model.is_default = True

        if model.is_default and sync_slot_default:
            self._upsert_slot_default_row(
                slot="chat",
                connection_id=model.connection_id,
                model_id=model.model_id,
                parameters=model.parameters_json,
            )

        self._session.flush()
        return model

    def list_chat_models(self) -> list[GlobalChatModel]:
        statement = select(GlobalChatModel).order_by(
            GlobalChatModel.is_default.desc(),
            GlobalChatModel.connection_id,
            GlobalChatModel.model_id,
        )
        return list(self._session.scalars(statement))

    def set_default_chat_model(
        self,
        *,
        connection_id: str,
        model_id: str,
    ) -> GlobalChatModel:
        model = self._get_chat_model(connection_id, _normalize_model_id(model_id))
        if model is None:
            raise ValueError("chat_model_not_found")
        self._clear_chat_defaults()
        model.is_default = True
        self.upsert_slot_default(
            slot="chat",
            connection_id=model.connection_id,
            model_id=model.model_id,
            parameters=model.parameters_json,
        )
        self._session.flush()
        return model

    def delete_chat_model(self, *, connection_id: str, model_id: str) -> bool:
        model = self._get_chat_model(connection_id, _normalize_model_id(model_id))
        if model is None:
            return False
        models = self.list_chat_models()
        if len(models) == 1:
            raise ValueError("cannot_delete_last_chat_model")
        if model.is_default:
            raise ValueError("cannot_delete_default_chat_model")
        self._session.delete(model)
        self._session.flush()
        return True

    def _get_chat_model(
        self,
        connection_id: str,
        model_id: str,
    ) -> GlobalChatModel | None:
        return self._session.get(GlobalChatModel, (connection_id, model_id))

    def _clear_chat_defaults(self) -> None:
        for model in self.list_chat_models():
            model.is_default = False

    def _require_connection(self, connection_id: str) -> ProviderConnection:
        connection = self._session.get(ProviderConnection, connection_id)
        if connection is None:
            raise ValueError("connection_not_found")
        return connection

    def _upsert_slot_default_row(
        self,
        *,
        slot: str,
        connection_id: str,
        model_id: str,
        parameters: Mapping[str, Any] | None,
    ) -> RuntimeSlotDefault:
        default = self.get_slot_default(slot)
        parameters_json = dict(parameters) if parameters is not None else None
        if default is None:
            default = RuntimeSlotDefault(
                slot=slot,
                connection_id=connection_id,
                model_id=model_id,
                parameters_json=parameters_json,
            )
            self._session.add(default)
        else:
            default.connection_id = connection_id
            default.model_id = model_id
            default.parameters_json = parameters_json
        return default


class ProjectRuntimeSettingsRepository:
    """Persistence and effective reads for project runtime overrides."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get_project_runtime_settings(self, project_id: UUID) -> ProjectRuntimeSettings:
        project = self._require_project(project_id)
        slot_overrides = {
            override.slot: override
            for override in self._list_slot_overrides(project.id)
        }
        global_defaults = {
            default.slot: default
            for default in RuntimeSettingsRepository(self._session).list_slot_defaults()
        }

        slots: list[EffectiveRuntimeSlot] = []
        for slot in RUNTIME_SLOT_VALUES:
            override = slot_overrides.get(slot)
            if override is not None:
                slots.append(
                    EffectiveRuntimeSlot(
                        slot=slot,
                        source="overridden",
                        connection_id=override.connection_id,
                        model_id=override.model_id,
                        parameters_json=override.parameters_json,
                    )
                )
                continue
            default = global_defaults.get(slot)
            if default is not None:
                slots.append(
                    EffectiveRuntimeSlot(
                        slot=slot,
                        source="inherited",
                        connection_id=default.connection_id,
                        model_id=default.model_id,
                        parameters_json=default.parameters_json,
                    )
                )

        return ProjectRuntimeSettings(
            project_id=project.id,
            slots=slots,
            chat_models=self._effective_chat_models(project.id),
            chat_retrieval=ChatRetrievalSettingsRepository(
                self._session
            ).get_effective_project_settings(project.id),
        )

    def upsert_slot_override(
        self,
        *,
        project_id: UUID,
        slot: str,
        connection_id: str,
        model_id: str,
        parameters: Mapping[str, Any] | None = None,
    ) -> ProjectRuntimeSlotOverride:
        project = self._require_project(project_id)
        slot = _normalize_slot(slot)
        model_id = _normalize_model_id(model_id)
        connection = self._require_connection(connection_id)
        _require_capability(connection, slot)
        override = self._upsert_slot_override_row(
            project_id=project.id,
            slot=slot,
            connection_id=connection.connection_id,
            model_id=model_id,
            parameters=parameters,
        )

        if slot == "chat":
            self.upsert_chat_model(
                project_id=project.id,
                connection_id=connection.connection_id,
                model_id=model_id,
                make_default=True,
                parameters=parameters,
                sync_slot_override=False,
            )

        self._session.flush()
        return override

    def delete_slot_override(self, *, project_id: UUID, slot: str) -> bool:
        project = self._require_project(project_id)
        slot = _normalize_slot(slot)
        override = self._session.get(ProjectRuntimeSlotOverride, (project.id, slot))
        if override is None:
            return False
        self._session.delete(override)
        self._session.flush()
        return True

    def upsert_chat_model(
        self,
        *,
        project_id: UUID,
        connection_id: str,
        model_id: str,
        make_default: bool = False,
        parameters: Mapping[str, Any] | None = None,
        sync_slot_override: bool = True,
    ) -> ProjectChatModel:
        project = self._require_project(project_id)
        model_id = _normalize_model_id(model_id)
        connection = self._require_connection(connection_id)
        _require_capability(connection, "chat")
        project_models = self._list_project_chat_models(project.id)
        should_be_default = make_default or len(project_models) == 0
        parameters_json = dict(parameters) if parameters is not None else None

        if should_be_default:
            self._clear_project_chat_defaults(project.id)

        model = self._get_project_chat_model(
            project_id=project.id,
            connection_id=connection.connection_id,
            model_id=model_id,
        )
        if model is None:
            model = ProjectChatModel(
                project_id=project.id,
                connection_id=connection.connection_id,
                model_id=model_id,
                is_default=should_be_default,
                parameters_json=parameters_json,
            )
            self._session.add(model)
        else:
            model.parameters_json = parameters_json
            if should_be_default:
                model.is_default = True

        if model.is_default and sync_slot_override:
            self._upsert_slot_override_row(
                project_id=project.id,
                slot="chat",
                connection_id=model.connection_id,
                model_id=model.model_id,
                parameters=model.parameters_json,
            )

        self._session.flush()
        return model

    def set_default_chat_model(
        self,
        *,
        project_id: UUID,
        connection_id: str,
        model_id: str,
    ) -> ProjectChatModel:
        project = self._require_project(project_id)
        model = self._get_project_chat_model(
            project_id=project.id,
            connection_id=connection_id,
            model_id=_normalize_model_id(model_id),
        )
        if model is None:
            raise ValueError("chat_model_not_found")
        self._clear_project_chat_defaults(project.id)
        model.is_default = True
        self._upsert_slot_override_row(
            project_id=project.id,
            slot="chat",
            connection_id=model.connection_id,
            model_id=model.model_id,
            parameters=model.parameters_json,
        )
        self._session.flush()
        return model

    def delete_chat_model(
        self,
        *,
        project_id: UUID,
        connection_id: str,
        model_id: str,
    ) -> bool:
        project = self._require_project(project_id)
        model = self._get_project_chat_model(
            project_id=project.id,
            connection_id=connection_id,
            model_id=_normalize_model_id(model_id),
        )
        if model is None:
            return False
        models = self._list_project_chat_models(project.id)
        if len(models) == 1:
            raise ValueError("cannot_delete_last_chat_model")
        if model.is_default:
            raise ValueError("cannot_delete_default_chat_model")
        self._session.delete(model)
        self._session.flush()
        return True

    def _effective_chat_models(self, project_id: UUID) -> list[EffectiveChatModel]:
        project_models = self._list_project_chat_models(project_id)
        if project_models:
            return [
                EffectiveChatModel(
                    connection_id=model.connection_id,
                    model_id=model.model_id,
                    is_default=model.is_default,
                    source="overridden",
                    parameters_json=model.parameters_json,
                )
                for model in project_models
            ]
        return [
            EffectiveChatModel(
                connection_id=model.connection_id,
                model_id=model.model_id,
                is_default=model.is_default,
                source="inherited",
                parameters_json=model.parameters_json,
            )
            for model in RuntimeSettingsRepository(self._session).list_chat_models()
        ]

    def _list_slot_overrides(
        self,
        project_id: UUID,
    ) -> list[ProjectRuntimeSlotOverride]:
        statement = (
            select(ProjectRuntimeSlotOverride)
            .where(ProjectRuntimeSlotOverride.project_id == project_id)
            .order_by(ProjectRuntimeSlotOverride.slot)
        )
        return list(self._session.scalars(statement))

    def _list_project_chat_models(self, project_id: UUID) -> list[ProjectChatModel]:
        statement = (
            select(ProjectChatModel)
            .where(ProjectChatModel.project_id == project_id)
            .order_by(
                ProjectChatModel.is_default.desc(),
                ProjectChatModel.connection_id,
                ProjectChatModel.model_id,
            )
        )
        return list(self._session.scalars(statement))

    def _get_project_chat_model(
        self,
        *,
        project_id: UUID,
        connection_id: str,
        model_id: str,
    ) -> ProjectChatModel | None:
        return self._session.get(
            ProjectChatModel,
            (project_id, connection_id, model_id),
        )

    def _clear_project_chat_defaults(self, project_id: UUID) -> None:
        for model in self._list_project_chat_models(project_id):
            model.is_default = False

    def _require_project(self, project_id: UUID) -> Project:
        project = self._session.get(Project, project_id)
        if project is None:
            raise ValueError("project_not_found")
        return project

    def _require_connection(self, connection_id: str) -> ProviderConnection:
        connection = self._session.get(ProviderConnection, connection_id)
        if connection is None:
            raise ValueError("connection_not_found")
        return connection

    def _upsert_slot_override_row(
        self,
        *,
        project_id: UUID,
        slot: str,
        connection_id: str,
        model_id: str,
        parameters: Mapping[str, Any] | None,
    ) -> ProjectRuntimeSlotOverride:
        override = self._session.get(ProjectRuntimeSlotOverride, (project_id, slot))
        parameters_json = dict(parameters) if parameters is not None else None
        if override is None:
            override = ProjectRuntimeSlotOverride(
                project_id=project_id,
                slot=slot,
                connection_id=connection_id,
                model_id=model_id,
                parameters_json=parameters_json,
            )
            self._session.add(override)
        else:
            override.connection_id = connection_id
            override.model_id = model_id
            override.parameters_json = parameters_json
        return override


def _normalize_slot(slot: str) -> str:
    normalized = slot.strip()
    if normalized not in RUNTIME_SLOT_VALUES:
        raise ValueError(f"unsupported_slot: {normalized}")
    return normalized


def _normalize_model_id(model_id: str) -> str:
    normalized = model_id.strip()
    if not normalized:
        raise ValueError("model_id must not be empty")
    return normalized


def _require_capability(connection: ProviderConnection, slot: str) -> None:
    if slot not in connection.capabilities_json:
        raise ValueError(
            f"connection_unavailable: {connection.connection_id} does not support "
            f"{slot}"
        )


def _validate_chat_retrieval_settings(
    *,
    retrieval_limit: int,
    rerank_enabled: bool,
    rerank_candidate_limit: int,
) -> None:
    _validate_limit(retrieval_limit, field_name="retrieval_limit")
    _validate_limit(rerank_candidate_limit, field_name="rerank_candidate_limit")
    if rerank_enabled and rerank_candidate_limit < retrieval_limit:
        raise ValueError(
            "rerank_candidate_limit must be greater than or equal to retrieval_limit"
        )


def _validate_limit(value: int, *, field_name: str) -> None:
    if value < 1 or value > CHAT_RETRIEVAL_MAX_LIMIT:
        raise ValueError(
            f"{field_name} must be between 1 and {CHAT_RETRIEVAL_MAX_LIMIT}"
        )
