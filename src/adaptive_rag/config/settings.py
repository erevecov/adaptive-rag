from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

VectorStoreName = Literal["pgvector"]
ProviderRuntimeMode = Literal["fake", "live"]
GraphStoreName = Literal["disabled", "neo4j"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="ADAPTIVE_RAG_",
        env_file=".env",
        env_file_encoding="utf-8",
        env_ignore_empty=True,
        extra="ignore",
    )

    env: str = "local"
    log_level: str = "INFO"
    database_url: str = (
        "postgresql+psycopg://adaptive_rag:adaptive_rag"
        "@localhost:5432/adaptive_rag"
    )
    cors_allowed_origins: tuple[str, ...] = (
        "http://localhost:3000",
        "http://localhost:3001",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
        "http://127.0.0.1:5173",
    )
    api_key: SecretStr | None = Field(default=None)
    vector_store: VectorStoreName = "pgvector"
    graph_store: GraphStoreName = "disabled"
    provider_runtime_mode: ProviderRuntimeMode = "fake"
    embedding_provider: str = "fake"
    embedding_model: str = "fake-embedding-v1"
    sparse_embedding_provider: str = "fake"
    sparse_embedding_model: str = "fake-sparse-embedding-v1"
    chat_provider: str = "fake"
    chat_model: str = "retrieval-grounded-local-v1"
    rerank_provider: str = "fake"
    rerank_model: str = "fake-rerank-v1"
    provider_timeout_seconds: float = 30.0
    provider_max_retries: int = 2
    provider_max_cost_usd: float | None = None
    provider_chat_input_price_per_million_tokens_usd: float | None = None
    provider_chat_output_price_per_million_tokens_usd: float | None = None
    provider_embedding_input_price_per_million_tokens_usd: float | None = None
    provider_rerank_input_price_per_million_tokens_usd: float | None = None
    provider_secrets_key: SecretStr | None = Field(default=None)
    provider_secrets_key_file: Path | None = Field(
        default=Path(".adaptive-rag/provider-secrets.key")
    )
    qwen_api_key: SecretStr | None = Field(default=None)
    qwen_base_url: str | None = Field(default=None)
    neo4j_uri: str | None = Field(default=None)
    neo4j_username: str | None = Field(default=None)
    neo4j_password: SecretStr | None = Field(default=None)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
