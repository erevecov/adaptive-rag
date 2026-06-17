from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

VectorStoreName = Literal["pgvector"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="ADAPTIVE_RAG_",
        env_file=".env",
        env_file_encoding="utf-8",
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


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
