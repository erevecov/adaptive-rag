from adaptive_rag.config.settings import Settings


def test_settings_use_adaptive_rag_env_prefix(monkeypatch):
    monkeypatch.setenv("ADAPTIVE_RAG_ENV", "test")
    monkeypatch.setenv("ADAPTIVE_RAG_DATABASE_URL", "sqlite+pysqlite:///:memory:")
    monkeypatch.setenv("ADAPTIVE_RAG_VECTOR_STORE", "pgvector")

    settings = Settings()

    assert settings.env == "test"
    assert settings.database_url == "sqlite+pysqlite:///:memory:"
    assert settings.vector_store == "pgvector"


def test_api_key_is_optional(monkeypatch):
    monkeypatch.delenv("ADAPTIVE_RAG_API_KEY", raising=False)

    settings = Settings()

    assert settings.api_key is None
