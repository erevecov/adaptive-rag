from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

VectorStoreName = Literal["pgvector"]
ProviderRuntimeMode = Literal["fake", "live"]


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
    api_key: str | None = Field(default=None)
    vector_store: VectorStoreName = "pgvector"
    provider_runtime_mode: ProviderRuntimeMode = "fake"
    embedding_provider: str = "fake"
    embedding_model: str = "fake-embedding-v1"
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
    qwen_api_key: SecretStr | None = Field(default=None)
    qwen_base_url: str | None = Field(default=None)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
