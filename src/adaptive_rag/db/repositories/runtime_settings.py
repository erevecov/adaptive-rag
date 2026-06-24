"""Repository for global runtime slot defaults and chat model pool."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from adaptive_rag.db.models import (
    RUNTIME_SLOT_VALUES,
    GlobalChatModel,
    ProviderConnection,
    RuntimeSlotDefault,
)


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
