"""Models for global runtime provider connections and encrypted secrets."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, LargeBinary, func
from sqlalchemy.orm import Mapped, mapped_column

from adaptive_rag.db.base import Base
from adaptive_rag.db.models.job import utc_now
from adaptive_rag.db.models.project import JSONWithJSONB

PROVIDER_CONNECTION_PROVIDER_VALUES = ("fake", "qwen", "local_openai_compatible")
PROVIDER_CONNECTION_TYPE_VALUES = ("fake", "hosted", "local")
PROVIDER_CONNECTION_CAPABILITY_VALUES = (
    "chat",
    "dense_embedding",
    "sparse_embedding",
    "rerank",
    "contextualization",
)
PROVIDER_SECRET_NAME_VALUES = ("api_key",)


class ProviderConnection(Base):
    """Global provider connection metadata without secret values."""

    __tablename__ = "provider_connections"
    __table_args__ = (
        CheckConstraint(
            "provider IN ('fake', 'qwen', 'local_openai_compatible')",
            name="provider_connections_provider_check",
        ),
        CheckConstraint(
            "connection_type IN ('fake', 'hosted', 'local')",
            name="provider_connections_connection_type_check",
        ),
    )

    connection_id: Mapped[str] = mapped_column(primary_key=True)
    provider: Mapped[str] = mapped_column(nullable=False)
    connection_type: Mapped[str] = mapped_column(nullable=False)
    base_url: Mapped[str | None] = mapped_column(nullable=True)
    capabilities_json: Mapped[list[str]] = mapped_column(
        JSONWithJSONB(), nullable=False
    )
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(
        JSONWithJSONB(), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

class ProviderSecret(Base):
    """Encrypted provider secret bound to a global connection."""

    __tablename__ = "provider_secrets"
    __table_args__ = (
        CheckConstraint(
            "secret_name IN ('api_key')",
            name="provider_secrets_secret_name_check",
        ),
    )

    connection_id: Mapped[str] = mapped_column(
        ForeignKey("provider_connections.connection_id", ondelete="CASCADE"),
        primary_key=True,
    )
    secret_name: Mapped[str] = mapped_column(primary_key=True)
    encrypted_value: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    fingerprint: Mapped[str | None] = mapped_column(nullable=True)
    last_four: Mapped[str | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class ProviderModelCatalog(Base):
    """Safe provider model metadata discovered for a global connection."""

    __tablename__ = "provider_model_catalog"

    connection_id: Mapped[str] = mapped_column(
        ForeignKey("provider_connections.connection_id", ondelete="CASCADE"),
        primary_key=True,
    )
    model_id: Mapped[str] = mapped_column(primary_key=True)
    capabilities_json: Mapped[list[str]] = mapped_column(
        JSONWithJSONB(), nullable=False
    )
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(
        JSONWithJSONB(), nullable=True
    )
    pricing_json: Mapped[dict[str, Any] | None] = mapped_column(
        JSONWithJSONB(), nullable=True
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        server_default=func.now(),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
