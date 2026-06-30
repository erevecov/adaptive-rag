"""Tests for provider secret encryption helpers."""

from __future__ import annotations

import base64
from pathlib import Path

import pytest

from adaptive_rag.config.settings import Settings
from adaptive_rag.provider_secrets import (
    ProviderSecretDecryptError,
    ProviderSecretKeyError,
    ProviderSecretStore,
)


def _fernet_key() -> str:
    return base64.urlsafe_b64encode(b"0" * 32).decode("ascii")


def test_provider_secret_store_encrypts_and_decrypts_without_plaintext_leak() -> None:
    store = ProviderSecretStore.from_settings(
        Settings(
            _env_file=None,
            provider_secrets_key=_fernet_key(),
            provider_secrets_key_file=None,
        )
    )

    token = store.encrypt("sk-hosted-secret")

    assert isinstance(token, bytes)
    assert token != b"sk-hosted-secret"
    assert b"sk-hosted-secret" not in token
    assert store.decrypt(token) == "sk-hosted-secret"


def test_provider_secret_store_creates_and_reuses_local_key_file(
    tmp_path: Path,
) -> None:
    key_file = tmp_path / "provider-secrets.key"
    settings = Settings(
        _env_file=None,
        provider_secrets_key=None,
        provider_secrets_key_file=key_file,
    )

    store = ProviderSecretStore.from_settings(settings)
    token = store.encrypt("sk-hosted-secret")
    second_store = ProviderSecretStore.from_settings(settings)

    assert key_file.exists()
    assert key_file.read_text(encoding="ascii").strip() != "sk-hosted-secret"
    assert second_store.decrypt(token) == "sk-hosted-secret"


def test_provider_secret_store_requires_configured_key_when_file_disabled() -> None:
    with pytest.raises(
        ProviderSecretKeyError,
        match="ADAPTIVE_RAG_PROVIDER_SECRETS_KEY is required",
    ):
        ProviderSecretStore.from_settings(
            Settings(
                _env_file=None,
                provider_secrets_key=None,
                provider_secrets_key_file=None,
            )
        )


def test_provider_secret_store_rejects_invalid_or_mismatched_tokens() -> None:
    store = ProviderSecretStore.from_settings(
        Settings(
            _env_file=None,
            provider_secrets_key=_fernet_key(),
            provider_secrets_key_file=None,
        )
    )

    with pytest.raises(
        ProviderSecretDecryptError,
        match="provider secret could not be decrypted",
    ):
        store.decrypt(b"not-a-fernet-token")


def test_provider_secret_store_rejects_invalid_key_file(tmp_path: Path) -> None:
    key_file = tmp_path / "provider-secrets.key"
    key_file.write_text("not-a-fernet-key\n", encoding="ascii")

    with pytest.raises(
        ProviderSecretKeyError,
        match="provider secrets key file is invalid",
    ):
        ProviderSecretStore.from_settings(
            Settings(
                _env_file=None,
                provider_secrets_key=None,
                provider_secrets_key_file=key_file,
            )
        )
