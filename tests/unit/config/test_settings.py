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


def test_api_key_setting_hides_value_when_configured(monkeypatch):
    monkeypatch.setenv("ADAPTIVE_RAG_API_KEY", "secret-api-key")

    settings = Settings()

    assert settings.api_key is not None
    assert settings.api_key.get_secret_value() == "secret-api-key"
    assert "secret-api-key" not in repr(settings)


def test_provider_runtime_settings_use_env_prefix(monkeypatch):
    monkeypatch.setenv("ADAPTIVE_RAG_PROVIDER_RUNTIME_MODE", "live")
    monkeypatch.setenv("ADAPTIVE_RAG_EMBEDDING_PROVIDER", "qwen")
    monkeypatch.setenv("ADAPTIVE_RAG_EMBEDDING_MODEL", "qwen-embedding-live-v1")
    monkeypatch.setenv("ADAPTIVE_RAG_CHAT_PROVIDER", "qwen")
    monkeypatch.setenv("ADAPTIVE_RAG_CHAT_MODEL", "qwen-chat-live-v1")
    monkeypatch.setenv("ADAPTIVE_RAG_RERANK_PROVIDER", "qwen")
    monkeypatch.setenv("ADAPTIVE_RAG_RERANK_MODEL", "qwen3-rerank")
    monkeypatch.setenv("ADAPTIVE_RAG_PROVIDER_TIMEOUT_SECONDS", "12.5")
    monkeypatch.setenv("ADAPTIVE_RAG_PROVIDER_MAX_RETRIES", "4")
    monkeypatch.setenv("ADAPTIVE_RAG_PROVIDER_MAX_COST_USD", "0.25")
    monkeypatch.setenv("ADAPTIVE_RAG_PROVIDER_SECRETS_KEY", "provider-secret-key")
    monkeypatch.setenv(
        "ADAPTIVE_RAG_PROVIDER_CHAT_INPUT_PRICE_PER_MILLION_TOKENS_USD",
        "2.0",
    )
    monkeypatch.setenv(
        "ADAPTIVE_RAG_PROVIDER_CHAT_OUTPUT_PRICE_PER_MILLION_TOKENS_USD",
        "6.0",
    )
    monkeypatch.setenv(
        "ADAPTIVE_RAG_PROVIDER_EMBEDDING_INPUT_PRICE_PER_MILLION_TOKENS_USD",
        "0.13",
    )
    monkeypatch.setenv(
        "ADAPTIVE_RAG_PROVIDER_RERANK_INPUT_PRICE_PER_MILLION_TOKENS_USD",
        "0.08",
    )
    monkeypatch.setenv("ADAPTIVE_RAG_QWEN_API_KEY", "sk-test-secret")
    monkeypatch.setenv("ADAPTIVE_RAG_QWEN_BASE_URL", "https://example.test/v1")

    settings = Settings()

    assert settings.provider_runtime_mode == "live"
    assert settings.embedding_provider == "qwen"
    assert settings.embedding_model == "qwen-embedding-live-v1"
    assert settings.chat_provider == "qwen"
    assert settings.chat_model == "qwen-chat-live-v1"
    assert settings.rerank_provider == "qwen"
    assert settings.rerank_model == "qwen3-rerank"
    assert settings.provider_timeout_seconds == 12.5
    assert settings.provider_max_retries == 4
    assert settings.provider_max_cost_usd == 0.25
    assert settings.provider_secrets_key is not None
    assert settings.provider_secrets_key.get_secret_value() == "provider-secret-key"
    assert settings.provider_chat_input_price_per_million_tokens_usd == 2.0
    assert settings.provider_chat_output_price_per_million_tokens_usd == 6.0
    assert settings.provider_embedding_input_price_per_million_tokens_usd == 0.13
    assert settings.provider_rerank_input_price_per_million_tokens_usd == 0.08
    assert settings.qwen_api_key is not None
    assert settings.qwen_api_key.get_secret_value() == "sk-test-secret"
    assert settings.qwen_base_url == "https://example.test/v1"
    assert "sk-test-secret" not in repr(settings)


def test_graph_store_settings_default_to_disabled_without_neo4j_credentials(
    monkeypatch,
):
    monkeypatch.delenv("ADAPTIVE_RAG_GRAPH_STORE", raising=False)
    monkeypatch.delenv("ADAPTIVE_RAG_NEO4J_URI", raising=False)
    monkeypatch.delenv("ADAPTIVE_RAG_NEO4J_USERNAME", raising=False)
    monkeypatch.delenv("ADAPTIVE_RAG_NEO4J_PASSWORD", raising=False)

    settings = Settings()

    assert settings.graph_store == "disabled"
    assert settings.neo4j_uri is None
    assert settings.neo4j_username is None
    assert settings.neo4j_password is None


def test_graph_store_settings_use_env_prefix_and_hide_password(monkeypatch):
    monkeypatch.setenv("ADAPTIVE_RAG_GRAPH_STORE", "neo4j")
    monkeypatch.setenv("ADAPTIVE_RAG_NEO4J_URI", "neo4j+s://graph.example.test")
    monkeypatch.setenv("ADAPTIVE_RAG_NEO4J_USERNAME", "neo4j")
    monkeypatch.setenv("ADAPTIVE_RAG_NEO4J_PASSWORD", "secret-password")

    settings = Settings()

    assert settings.graph_store == "neo4j"
    assert settings.neo4j_uri == "neo4j+s://graph.example.test"
    assert settings.neo4j_username == "neo4j"
    assert settings.neo4j_password is not None
    assert settings.neo4j_password.get_secret_value() == "secret-password"
    assert "secret-password" not in repr(settings)


def test_empty_optional_env_values_are_ignored(tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "\n".join(
            [
                "ADAPTIVE_RAG_PROVIDER_MAX_COST_USD=",
                "ADAPTIVE_RAG_PROVIDER_CHAT_INPUT_PRICE_PER_MILLION_TOKENS_USD=",
                "ADAPTIVE_RAG_PROVIDER_CHAT_OUTPUT_PRICE_PER_MILLION_TOKENS_USD=",
                "ADAPTIVE_RAG_PROVIDER_EMBEDDING_INPUT_PRICE_PER_MILLION_TOKENS_USD=",
                "ADAPTIVE_RAG_PROVIDER_RERANK_INPUT_PRICE_PER_MILLION_TOKENS_USD=",
                "ADAPTIVE_RAG_PROVIDER_SECRETS_KEY=",
                "ADAPTIVE_RAG_QWEN_API_KEY=",
                "ADAPTIVE_RAG_QWEN_BASE_URL=",
            ]
        ),
        encoding="utf-8",
    )

    settings = Settings(_env_file=env_file)

    assert settings.provider_max_cost_usd is None
    assert settings.provider_chat_input_price_per_million_tokens_usd is None
    assert settings.provider_chat_output_price_per_million_tokens_usd is None
    assert settings.provider_embedding_input_price_per_million_tokens_usd is None
    assert settings.provider_rerank_input_price_per_million_tokens_usd is None
    assert settings.provider_secrets_key is None
    assert settings.qwen_api_key is None
    assert settings.qwen_base_url is None
