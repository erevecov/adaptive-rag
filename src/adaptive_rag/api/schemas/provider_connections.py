"""Schemas HTTP for runtime provider connections and secret status."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from adaptive_rag.db.models import ProviderConnection
from adaptive_rag.db.repositories import ProviderSecretStatus


class ProviderConnectionUpsertRequestBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider: str
    connection_type: str
    base_url: str | None = None
    capabilities: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] | None = None


class ProviderSecretUpsertRequestBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    value: str = Field(min_length=1)


class ProviderSecretStatusResponse(BaseModel):
    connection_id: str
    secret_name: str
    configured: bool
    updated_at: datetime | None
    last_four: str | None
    fingerprint: str | None

    @classmethod
    def from_status(cls, status: ProviderSecretStatus) -> ProviderSecretStatusResponse:
        return cls(
            connection_id=status.connection_id,
            secret_name=status.secret_name,
            configured=status.configured,
            updated_at=status.updated_at,
            last_four=status.last_four,
            fingerprint=status.fingerprint,
        )


class ProviderConnectionResponse(BaseModel):
    connection_id: str
    provider: str
    connection_type: str
    base_url: str | None
    capabilities: list[str]
    metadata: dict[str, Any] | None
    secrets: list[ProviderSecretStatusResponse]
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_connection(
        cls,
        connection: ProviderConnection,
        *,
        secrets: list[ProviderSecretStatus],
    ) -> ProviderConnectionResponse:
        return cls(
            connection_id=connection.connection_id,
            provider=connection.provider,
            connection_type=connection.connection_type,
            base_url=connection.base_url,
            capabilities=list(connection.capabilities_json),
            metadata=connection.metadata_json,
            secrets=[
                ProviderSecretStatusResponse.from_status(status)
                for status in secrets
            ],
            created_at=connection.created_at,
            updated_at=connection.updated_at,
        )


class ProviderConnectionListResponse(BaseModel):
    items: list[ProviderConnectionResponse]
