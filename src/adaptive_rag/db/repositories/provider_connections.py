"""Repository for global provider connections and encrypted secret status."""

from __future__ import annotations

import hashlib
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from adaptive_rag.db.models import (
    PROVIDER_CONNECTION_CAPABILITY_VALUES,
    PROVIDER_CONNECTION_PROVIDER_VALUES,
    PROVIDER_CONNECTION_TYPE_VALUES,
    PROVIDER_SECRET_NAME_VALUES,
    ProviderConnection,
    ProviderModelCatalog,
    ProviderSecret,
)
from adaptive_rag.db.models.job import utc_now
from adaptive_rag.provider_secrets import ProviderSecretStore


@dataclass(frozen=True)
class ProviderSecretStatus:
    """Safe-to-serialize status for a persisted provider secret."""

    connection_id: str
    secret_name: str
    configured: bool
    updated_at: datetime | None
    last_four: str | None
    fingerprint: str | None


class ProviderConnectionRepository:
    """Persistence for global provider connections.

    Transactions are controlled by the caller. Repository methods flush but do
    not commit.
    """

    def __init__(self, session: Session) -> None:
        self._session = session

    def create_connection(
        self,
        *,
        provider: str,
        connection_type: str,
        capabilities: Iterable[str],
        base_url: str | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> ProviderConnection:
        provider = _normalize_supported_value(
            provider,
            supported=PROVIDER_CONNECTION_PROVIDER_VALUES,
            label="provider",
        )
        connection_type = _normalize_supported_value(
            connection_type,
            supported=PROVIDER_CONNECTION_TYPE_VALUES,
            label="connection_type",
        )
        for _attempt in range(20):
            connection_id = _generated_connection_id(provider, connection_type)
            if self.get_connection(connection_id) is None:
                return self.upsert_connection(
                    connection_id=connection_id,
                    provider=provider,
                    connection_type=connection_type,
                    base_url=base_url,
                    capabilities=capabilities,
                    metadata=metadata,
                )
        raise ValueError("connection_id generation exhausted")

    def upsert_connection(
        self,
        *,
        connection_id: str,
        provider: str,
        connection_type: str,
        capabilities: Iterable[str],
        base_url: str | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> ProviderConnection:
        connection_id = _normalize_identifier(connection_id, "connection_id")
        provider = _normalize_supported_value(
            provider,
            supported=PROVIDER_CONNECTION_PROVIDER_VALUES,
            label="provider",
        )
        connection_type = _normalize_supported_value(
            connection_type,
            supported=PROVIDER_CONNECTION_TYPE_VALUES,
            label="connection_type",
        )
        normalized_capabilities = _normalize_capabilities(capabilities)
        metadata_json = dict(metadata) if metadata is not None else None

        connection = self.get_connection(connection_id)
        if connection is None:
            connection = ProviderConnection(
                connection_id=connection_id,
                provider=provider,
                connection_type=connection_type,
                base_url=base_url,
                capabilities_json=normalized_capabilities,
                metadata_json=metadata_json,
            )
            self._session.add(connection)
        else:
            connection.provider = provider
            connection.connection_type = connection_type
            connection.base_url = base_url
            connection.capabilities_json = normalized_capabilities
            connection.metadata_json = metadata_json

        self._session.flush()
        return connection

    def get_connection(self, connection_id: str) -> ProviderConnection | None:
        return self._session.get(ProviderConnection, connection_id)

    def list_connections(self) -> list[ProviderConnection]:
        statement = select(ProviderConnection).order_by(
            ProviderConnection.connection_id
        )
        return list(self._session.scalars(statement))

    def delete_connection(self, connection_id: str) -> bool:
        connection = self.get_connection(connection_id)
        if connection is None:
            return False
        self._session.execute(
            delete(ProviderSecret).where(ProviderSecret.connection_id == connection_id)
        )
        self._session.delete(connection)
        self._session.flush()
        return True

    def upsert_secret(
        self,
        *,
        connection_id: str,
        secret_name: str,
        secret_value: str,
        secret_store: ProviderSecretStore,
    ) -> ProviderSecretStatus:
        if self.get_connection(connection_id) is None:
            raise ValueError("connection not found")
        secret_name = _normalize_supported_value(
            secret_name,
            supported=PROVIDER_SECRET_NAME_VALUES,
            label="secret_name",
        )
        if not secret_value:
            raise ValueError("secret value must not be empty")

        encrypted_value = secret_store.encrypt(secret_value)
        fingerprint = hashlib.sha256(secret_value.encode("utf-8")).hexdigest()
        last_four = secret_value[-4:] if len(secret_value) >= 4 else secret_value

        secret = self._session.get(ProviderSecret, (connection_id, secret_name))
        if secret is None:
            secret = ProviderSecret(
                connection_id=connection_id,
                secret_name=secret_name,
                encrypted_value=encrypted_value,
                fingerprint=fingerprint,
                last_four=last_four,
            )
            self._session.add(secret)
        else:
            secret.encrypted_value = encrypted_value
            secret.fingerprint = fingerprint
            secret.last_four = last_four

        self._session.flush()
        return _secret_status(secret)

    def delete_secret(self, *, connection_id: str, secret_name: str) -> bool:
        secret_name = _normalize_supported_value(
            secret_name,
            supported=PROVIDER_SECRET_NAME_VALUES,
            label="secret_name",
        )
        secret = self._session.get(ProviderSecret, (connection_id, secret_name))
        if secret is None:
            return False
        self._session.delete(secret)
        self._session.flush()
        return True

    def list_secret_statuses(self, connection_id: str) -> list[ProviderSecretStatus]:
        statement = (
            select(ProviderSecret)
            .where(ProviderSecret.connection_id == connection_id)
            .order_by(ProviderSecret.secret_name)
        )
        return [_secret_status(secret) for secret in self._session.scalars(statement)]


class ProviderModelCatalogRepository:
    """Persistence for provider model IDs discovered per connection."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def upsert_model(
        self,
        *,
        connection_id: str,
        model_id: str,
        capabilities: Iterable[str],
        metadata: Mapping[str, Any] | None = None,
        pricing: Mapping[str, Any] | None = None,
    ) -> ProviderModelCatalog:
        if self._session.get(ProviderConnection, connection_id) is None:
            raise ValueError("connection_not_found")
        model_id = _normalize_identifier(model_id, "model_id")
        capabilities_json = _normalize_model_capabilities(capabilities)
        metadata_json = dict(metadata) if metadata is not None else None
        pricing_json = dict(pricing) if pricing is not None else None

        model = self._session.get(ProviderModelCatalog, (connection_id, model_id))
        now = utc_now()
        if model is None:
            model = ProviderModelCatalog(
                connection_id=connection_id,
                model_id=model_id,
                capabilities_json=capabilities_json,
                metadata_json=metadata_json,
                pricing_json=pricing_json,
                last_seen_at=now,
            )
            self._session.add(model)
        else:
            model.capabilities_json = capabilities_json
            model.metadata_json = metadata_json
            model.pricing_json = pricing_json
            model.last_seen_at = now

        self._session.flush()
        return model

    def list_models(
        self,
        *,
        connection_id: str | None = None,
        capability: str | None = None,
    ) -> list[ProviderModelCatalog]:
        statement = select(ProviderModelCatalog)
        if connection_id is not None:
            statement = statement.where(
                ProviderModelCatalog.connection_id == connection_id
            )
        models = list(
            self._session.scalars(
                statement.order_by(
                    ProviderModelCatalog.connection_id,
                    ProviderModelCatalog.model_id,
                )
            )
        )
        if capability is None or capability.strip() == "":
            return models
        normalized = _normalize_supported_value(
            capability,
            supported=PROVIDER_CONNECTION_CAPABILITY_VALUES,
            label="provider capability",
        )
        return [
            model for model in models if normalized in model.capabilities_json
        ]


def _secret_status(secret: ProviderSecret) -> ProviderSecretStatus:
    return ProviderSecretStatus(
        connection_id=secret.connection_id,
        secret_name=secret.secret_name,
        configured=True,
        updated_at=secret.updated_at,
        last_four=secret.last_four,
        fingerprint=secret.fingerprint,
    )


def _normalize_identifier(value: str, label: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{label} must not be empty")
    return normalized


def _normalize_supported_value(
    value: str,
    *,
    supported: tuple[str, ...],
    label: str,
) -> str:
    normalized = value.strip()
    if normalized not in supported:
        raise ValueError(f"unsupported {label}: {normalized}")
    return normalized


def _normalize_capabilities(capabilities: Iterable[str]) -> list[str]:
    requested = set()
    for capability in capabilities:
        normalized = capability.strip()
        if normalized not in PROVIDER_CONNECTION_CAPABILITY_VALUES:
            raise ValueError(f"unsupported provider capability: {normalized}")
        requested.add(normalized)
    if not requested:
        raise ValueError("provider connection requires at least one capability")
    return [
        capability
        for capability in PROVIDER_CONNECTION_CAPABILITY_VALUES
        if capability in requested
    ]


def _normalize_model_capabilities(capabilities: Iterable[str]) -> list[str]:
    requested = set()
    for capability in capabilities:
        normalized = capability.strip()
        if normalized not in PROVIDER_CONNECTION_CAPABILITY_VALUES:
            raise ValueError(f"unsupported provider capability: {normalized}")
        requested.add(normalized)
    return [
        capability
        for capability in PROVIDER_CONNECTION_CAPABILITY_VALUES
        if capability in requested
    ]


def _generated_connection_id(provider: str, connection_type: str) -> str:
    return f"{provider}-{connection_type}-{uuid4().hex[:8]}"
