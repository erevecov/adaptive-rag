"""Unit tests for human password and opaque-session primitives."""

from __future__ import annotations

import hashlib

import pytest
from argon2 import PasswordHasher

from adaptive_rag.security.human_auth import (
    PasswordService,
    generate_temporary_password,
    hash_opaque_secret,
    normalize_email,
    validate_password,
)


def test_normalize_email_strips_and_case_folds() -> None:
    assert normalize_email("  Ada.Lovelace@Example.COM  ") == (
        "ada.lovelace@example.com"
    )


@pytest.mark.parametrize("value", ["", "plain-address", "@example.com", "a@"])
def test_normalize_email_rejects_invalid_addresses(value: str) -> None:
    with pytest.raises(ValueError, match="invalid_email"):
        normalize_email(value)


def test_password_policy_accepts_unicode_and_has_length_bounds() -> None:
    assert validate_password("correct horse batería segura") == (
        "correct horse batería segura"
    )

    with pytest.raises(ValueError, match="password_too_short"):
        validate_password("short")
    with pytest.raises(ValueError, match="password_too_long"):
        validate_password("x" * 129)


def test_password_service_hashes_argon2id_and_verifies_without_raising() -> None:
    service = PasswordService(
        hasher=PasswordHasher(time_cost=1, memory_cost=1024, parallelism=1)
    )

    encoded = service.hash("correct horse battery staple")

    assert encoded.startswith("$argon2id$")
    assert service.verify(encoded, "correct horse battery staple") is True
    assert service.verify(encoded, "wrong password value") is False


def test_default_password_service_uses_approved_minimum_parameters() -> None:
    service = PasswordService()
    parameters = service.parameters

    assert parameters.type == "argon2id"
    assert parameters.memory_cost_kib >= 19 * 1024
    assert parameters.time_cost >= 2
    assert parameters.parallelism == 1


def test_hash_opaque_secret_is_stable_prefixed_and_not_plaintext() -> None:
    digest = hashlib.sha256(b"session secret").hexdigest()

    assert hash_opaque_secret("session secret") == f"sha256:{digest}"
    assert "session secret" not in hash_opaque_secret("session secret")


def test_temporary_password_uses_high_entropy_urlsafe_value() -> None:
    first = generate_temporary_password()
    second = generate_temporary_password()

    assert len(first) >= 43
    assert first != second
    assert validate_password(first) == first
