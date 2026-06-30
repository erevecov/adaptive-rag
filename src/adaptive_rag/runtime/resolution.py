"""Runtime slot resolution from persisted settings and legacy environment."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from adaptive_rag.config.settings import Settings
from adaptive_rag.db.models import ProviderConnection, ProviderSecret
from adaptive_rag.db.repositories import (
    EffectiveChatModel,
    EffectiveRuntimeSlot,
    ProjectRuntimeSettingsRepository,
    RuntimeSettingsRepository,
)
from adaptive_rag.provider_secrets import (
    ProviderSecretDecryptError,
    ProviderSecretStore,
)


class ProviderConfigurationError(ValueError):
    """Error estable de configuracion para providers live."""


@dataclass(frozen=True, slots=True)
class ResolvedRuntimeSlot:
    """Runtime slot resolved from persisted settings."""

    slot: str
    provider: str
    connection_id: str
    model_id: str
    base_url: str | None
    parameters: dict[str, Any] | None
    api_key: str | None = field(repr=False)


def _resolve_persisted_slot(
    slot: str,
    settings: Settings,
    *,
    project_id: UUID | None,
    secret_store: ProviderSecretStore | None,
    session: Session | None,
) -> ResolvedRuntimeSlot | None:
    if session is None:
        return None

    if project_id is None:
        runtime_settings_repository = RuntimeSettingsRepository(session)
        if slot == "chat":
            chat_model = _global_chat_model(
                runtime_settings_repository.list_chat_models()
            )
            if chat_model is not None:
                connection_id = chat_model.connection_id
                model_id = chat_model.model_id
                parameters = chat_model.parameters_json
            else:
                slot_default = runtime_settings_repository.get_slot_default(slot)
                if slot_default is None:
                    return None
                connection_id = slot_default.connection_id
                model_id = slot_default.model_id
                parameters = slot_default.parameters_json
        else:
            slot_default = runtime_settings_repository.get_slot_default(slot)
            if slot_default is None:
                return None
            connection_id = slot_default.connection_id
            model_id = slot_default.model_id
            parameters = slot_default.parameters_json
    else:
        try:
            runtime_settings = ProjectRuntimeSettingsRepository(
                session
            ).get_project_runtime_settings(project_id)
        except ValueError as exc:
            raise ProviderConfigurationError(str(exc)) from exc

        effective_chat_model = (
            _effective_chat_model(runtime_settings.chat_models)
            if slot == "chat"
            else None
        )
        if effective_chat_model is not None:
            connection_id = effective_chat_model.connection_id
            model_id = effective_chat_model.model_id
            parameters = effective_chat_model.parameters_json
        else:
            effective_slot = _effective_slot(runtime_settings.slots, slot)
            if effective_slot is None:
                return None
            connection_id = effective_slot.connection_id
            model_id = effective_slot.model_id
            parameters = effective_slot.parameters_json

    connection = session.get(ProviderConnection, connection_id)
    if connection is None:
        raise ProviderConfigurationError(f"connection_not_found: {connection_id}")
    return _resolved_slot(
        slot=slot,
        model_id=model_id,
        parameters=parameters,
        connection=connection,
        secret_store=secret_store,
        session=session,
        settings=settings,
    )


def _effective_slot(
    slots: list[EffectiveRuntimeSlot],
    slot: str,
) -> EffectiveRuntimeSlot | None:
    for item in slots:
        if item.slot == slot:
            return item
    return None


def _global_chat_model(chat_models: list[Any]) -> Any | None:
    for model in chat_models:
        if model.is_default:
            return model
    return None


def _effective_chat_model(
    chat_models: list[EffectiveChatModel],
) -> EffectiveChatModel | None:
    for model in chat_models:
        if model.is_default:
            return model
    return None


def _resolved_slot(
    *,
    slot: str,
    model_id: str,
    parameters: dict[str, Any] | None,
    connection: ProviderConnection,
    secret_store: ProviderSecretStore | None,
    session: Session,
    settings: Settings,
) -> ResolvedRuntimeSlot:
    api_key = _api_key_for_connection(
        connection,
        secret_store=secret_store,
        session=session,
        settings=settings,
    )
    base_url = _base_url_for_connection(connection, settings)
    return ResolvedRuntimeSlot(
        slot=slot,
        provider=connection.provider,
        connection_id=connection.connection_id,
        model_id=model_id,
        base_url=base_url,
        parameters=parameters,
        api_key=api_key,
    )


def _api_key_for_connection(
    connection: ProviderConnection,
    *,
    secret_store: ProviderSecretStore | None,
    session: Session,
    settings: Settings,
) -> str | None:
    if connection.provider == "fake":
        return None

    secret = session.get(ProviderSecret, (connection.connection_id, "api_key"))
    if secret is not None:
        active_store = secret_store or ProviderSecretStore.from_settings(settings)
        try:
            return active_store.decrypt(secret.encrypted_value)
        except ProviderSecretDecryptError as exc:
            raise ProviderConfigurationError(
                f"provider_secret_decrypt_failed: {connection.connection_id} api_key"
            ) from exc

    if connection.provider == "qwen" and settings.qwen_api_key is not None:
        return settings.qwen_api_key.get_secret_value()
    if connection.provider == "local_openai_compatible":
        return ""
    raise ProviderConfigurationError(
        f"missing_provider_secret: {connection.connection_id} api_key is required"
    )


def _base_url_for_connection(
    connection: ProviderConnection,
    settings: Settings,
) -> str | None:
    if connection.provider == "fake":
        return None
    if connection.base_url:
        return connection.base_url
    if connection.provider == "qwen" and settings.qwen_base_url:
        return settings.qwen_base_url
    raise ProviderConfigurationError(
        f"missing_provider_base_url: {connection.connection_id} base_url is required"
    )
