"""Security primitives for local human authentication."""

from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass

from argon2 import PasswordHasher
from argon2.exceptions import VerificationError
from argon2.low_level import Type

MIN_PASSWORD_LENGTH = 15
MAX_PASSWORD_LENGTH = 128
ARGON2_MEMORY_COST_KIB = 19 * 1024
ARGON2_TIME_COST = 2
ARGON2_PARALLELISM = 1


@dataclass(frozen=True)
class PasswordParameters:
    type: str
    memory_cost_kib: int
    time_cost: int
    parallelism: int


class PasswordService:
    """Argon2id hashing with explicit, reviewable production parameters."""

    def __init__(self, *, hasher: PasswordHasher | None = None) -> None:
        self._hasher = hasher or PasswordHasher(
            time_cost=ARGON2_TIME_COST,
            memory_cost=ARGON2_MEMORY_COST_KIB,
            parallelism=ARGON2_PARALLELISM,
            type=Type.ID,
        )

    @property
    def parameters(self) -> PasswordParameters:
        return PasswordParameters(
            type=f"argon2{self._hasher.type.name.lower()}",
            memory_cost_kib=self._hasher.memory_cost,
            time_cost=self._hasher.time_cost,
            parallelism=self._hasher.parallelism,
        )

    def hash(self, password: str) -> str:
        return self._hasher.hash(validate_password(password))

    def verify(self, encoded_hash: str, password: str) -> bool:
        try:
            validate_password(password)
            return self._hasher.verify(encoded_hash, password)
        except (ValueError, VerificationError):
            return False

    def needs_rehash(self, encoded_hash: str) -> bool:
        try:
            return self._hasher.check_needs_rehash(encoded_hash)
        except VerificationError:
            return False


def normalize_email(value: str) -> str:
    normalized = value.strip().casefold()
    if (
        not normalized
        or len(normalized) > 320
        or normalized.count("@") != 1
        or any(character.isspace() for character in normalized)
    ):
        raise ValueError("invalid_email")
    local, domain = normalized.split("@", 1)
    if (
        not local
        or not domain
        or local.startswith(".")
        or local.endswith(".")
        or domain.startswith(".")
        or domain.endswith(".")
        or "." in (local[:1], domain[:1])
    ):
        raise ValueError("invalid_email")
    return normalized


def validate_password(value: str) -> str:
    if len(value) < MIN_PASSWORD_LENGTH:
        raise ValueError("password_too_short")
    if len(value) > MAX_PASSWORD_LENGTH:
        raise ValueError("password_too_long")
    return value


def generate_temporary_password() -> str:
    return secrets.token_urlsafe(32)


def generate_opaque_token() -> str:
    return secrets.token_urlsafe(32)


def hash_opaque_secret(value: str) -> str:
    if not value:
        raise ValueError("secret_must_not_be_empty")
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()
    return f"sha256:{digest}"
