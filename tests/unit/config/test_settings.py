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


def test_provider_runtime_settings_use_env_prefix(monkeypatch):
    monkeypatch.setenv("ADAPTIVE_RAG_PROVIDER_RUNTIME_MODE", "live")
    monkeypatch.setenv("ADAPTIVE_RAG_EMBEDDING_PROVIDER", "qwen")
    monkeypatch.setenv("ADAPTIVE_RAG_EMBEDDING_MODEL", "qwen-embedding-live-v1")
    monkeypatch.setenv("ADAPTIVE_RAG_CHAT_PROVIDER", "qwen")
    monkeypatch.setenv("ADAPTIVE_RAG_CHAT_MODEL", "qwen-chat-live-v1")
    monkeypatch.setenv("ADAPTIVE_RAG_PROVIDER_TIMEOUT_SECONDS", "12.5")
    monkeypatch.setenv("ADAPTIVE_RAG_PROVIDER_MAX_RETRIES", "4")
    monkeypatch.setenv("ADAPTIVE_RAG_PROVIDER_MAX_COST_USD", "0.25")
    monkeypatch.setenv("ADAPTIVE_RAG_QWEN_API_KEY", "sk-test-secret")
    monkeypatch.setenv("ADAPTIVE_RAG_QWEN_BASE_URL", "https://example.test/v1")

    settings = Settings()

    assert settings.provider_runtime_mode == "live"
    assert settings.embedding_provider == "qwen"
    assert settings.embedding_model == "qwen-embedding-live-v1"
    assert settings.chat_provider == "qwen"
    assert settings.chat_model == "qwen-chat-live-v1"
    assert settings.provider_timeout_seconds == 12.5
    assert settings.provider_max_retries == 4
    assert settings.provider_max_cost_usd == 0.25
    assert settings.qwen_api_key is not None
    assert settings.qwen_api_key.get_secret_value() == "sk-test-secret"
    assert settings.qwen_base_url == "https://example.test/v1"
    assert "sk-test-secret" not in repr(settings)


def test_empty_optional_env_values_are_ignored(tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "\n".join(
            [
                "ADAPTIVE_RAG_PROVIDER_MAX_COST_USD=",
                "ADAPTIVE_RAG_QWEN_API_KEY=",
                "ADAPTIVE_RAG_QWEN_BASE_URL=",
            ]
        ),
        encoding="utf-8",
    )

    settings = Settings(_env_file=env_file)

    assert settings.provider_max_cost_usd is None
    assert settings.qwen_api_key is None
    assert settings.qwen_base_url is None
