"""Encrypted storage helpers for global provider secrets."""

from __future__ import annotations

import os
from pathlib import Path

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
        if runtime_settings.provider_secrets_key is not None:
            return cls(runtime_settings.provider_secrets_key.get_secret_value())
        if runtime_settings.provider_secrets_key_file is None:
            raise ProviderSecretKeyError(
                "ADAPTIVE_RAG_PROVIDER_SECRETS_KEY is required"
            )
        return cls(_read_or_create_key_file(runtime_settings.provider_secrets_key_file))

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


def _read_or_create_key_file(path: Path) -> str:
    try:
        key = path.read_text(encoding="ascii").strip()
    except FileNotFoundError:
        key = _create_key_file(path)
    try:
        Fernet(key)
    except (TypeError, ValueError) as exc:
        raise ProviderSecretKeyError("provider secrets key file is invalid") from exc
    return key


def _create_key_file(path: Path) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    key = Fernet.generate_key().decode("ascii")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_BINARY"):
        flags |= os.O_BINARY
    try:
        descriptor = os.open(path, flags, 0o600)
    except FileExistsError:
        return path.read_text(encoding="ascii").strip()
    with os.fdopen(descriptor, "w", encoding="ascii", newline="\n") as file:
        file.write(f"{key}\n")
    return key
