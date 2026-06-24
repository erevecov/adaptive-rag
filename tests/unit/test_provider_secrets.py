"""Tests for provider secret encryption helpers."""

from __future__ import annotations

import base64

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
        Settings(_env_file=None, provider_secrets_key=_fernet_key())
    )

    token = store.encrypt("sk-hosted-secret")

    assert isinstance(token, bytes)
    assert token != b"sk-hosted-secret"
    assert b"sk-hosted-secret" not in token
    assert store.decrypt(token) == "sk-hosted-secret"


def test_provider_secret_store_requires_configured_key() -> None:
    with pytest.raises(
        ProviderSecretKeyError,
        match="ADAPTIVE_RAG_PROVIDER_SECRETS_KEY is required",
    ):
        ProviderSecretStore.from_settings(
            Settings(_env_file=None, provider_secrets_key=None)
        )


def test_provider_secret_store_rejects_invalid_or_mismatched_tokens() -> None:
    store = ProviderSecretStore.from_settings(
        Settings(_env_file=None, provider_secrets_key=_fernet_key())
    )

    with pytest.raises(
        ProviderSecretDecryptError,
        match="provider secret could not be decrypted",
    ):
        store.decrypt(b"not-a-fernet-token")
