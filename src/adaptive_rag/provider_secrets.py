"""Encrypted storage helpers for global provider secrets."""

from __future__ import annotations

from cryptography.fernet import Fernet, InvalidToken

from adaptive_rag.config.settings import Settings, get_settings


class ProviderSecretKeyError(ValueError):
    """Stable error for missing or invalid provider secret encryption keys."""


class ProviderSecretDecryptError(ValueError):
    """Stable error for encrypted provider secret decrypt failures."""


class ProviderSecretStore:
    """Encrypts/decrypts provider secrets with a server-side Fernet key."""

    def __init__(self, key: str | bytes) -> None:
        try:
            self._fernet = Fernet(key)
        except (TypeError, ValueError) as exc:
            raise ProviderSecretKeyError(
                "ADAPTIVE_RAG_PROVIDER_SECRETS_KEY is invalid"
            ) from exc

    @classmethod
    def from_settings(cls, settings: Settings | None = None) -> ProviderSecretStore:
        runtime_settings = settings or get_settings()
        if runtime_settings.provider_secrets_key is None:
            raise ProviderSecretKeyError(
                "ADAPTIVE_RAG_PROVIDER_SECRETS_KEY is required"
            )
        return cls(runtime_settings.provider_secrets_key.get_secret_value())

    def encrypt(self, plaintext: str) -> bytes:
        return self._fernet.encrypt(plaintext.encode("utf-8"))

    def decrypt(self, token: bytes) -> str:
        try:
            plaintext = self._fernet.decrypt(token)
            return plaintext.decode("utf-8")
        except (InvalidToken, TypeError, UnicodeDecodeError) as exc:
            raise ProviderSecretDecryptError(
                "provider secret could not be decrypted"
            ) from exc
