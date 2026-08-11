"""Repository tests for password credentials and human sessions."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from adaptive_rag.db.base import Base
from adaptive_rag.db.models import (
    LoginAttempt,
    User,
    UserPasswordCredential,
    UserSession,
)
from adaptive_rag.db.repositories import HumanAuthRepository, UserRepository
from adaptive_rag.db.session import create_engine_from_url, create_session_factory


def _make_session():
    engine = create_engine_from_url("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(
        engine,
        tables=[
            User.__table__,
            UserPasswordCredential.__table__,
            UserSession.__table__,
            LoginAttempt.__table__,
        ],
    )
    return create_session_factory(engine)()


def test_user_repository_uses_unique_normalized_email() -> None:
    session = _make_session()
    repo = UserRepository(session)

    user = repo.create_user(
        email="  Owner@Example.com ",
        display_name="Owner",
        system_role="superadmin",
    )

    assert user.email == "owner@example.com"
    assert repo.get_by_email(" OWNER@example.com ") == user


def test_password_credential_create_and_replace() -> None:
    session = _make_session()
    user = UserRepository(session).create_user(
        email="member@example.com", display_name="Member"
    )
    repo = HumanAuthRepository(session)

    credential = repo.set_password(
        user_id=user.id,
        password_hash="$argon2id$first",
        must_change_password=True,
    )
    changed_at = datetime(2026, 8, 11, tzinfo=UTC)
    replaced = repo.set_password(
        user_id=user.id,
        password_hash="$argon2id$second",
        must_change_password=False,
        password_changed_at=changed_at,
    )

    assert replaced is credential
    assert replaced.password_hash == "$argon2id$second"
    assert replaced.must_change_password is False
    assert replaced.password_changed_at == changed_at


def test_session_lookup_enforces_revocation_idle_absolute_and_active_user() -> None:
    session = _make_session()
    user = UserRepository(session).create_user(
        email="member@example.com", display_name="Member"
    )
    repo = HumanAuthRepository(session)
    now = datetime(2026, 8, 11, 12, tzinfo=UTC)
    active = repo.create_session(
        user_id=user.id,
        token_hash="sha256:active",
        csrf_token_hash="sha256:csrf",
        now=now,
        expires_at=now + timedelta(days=7),
    )

    resolved = repo.get_active_session(
        token_hash="sha256:active",
        now=now + timedelta(hours=11),
        idle_timeout=timedelta(hours=12),
    )
    assert resolved == active
    assert active.last_seen_at == now + timedelta(hours=11)

    assert (
        repo.get_active_session(
            token_hash="sha256:active",
            now=now + timedelta(hours=24),
            idle_timeout=timedelta(hours=12),
        )
        is None
    )

    absolute = repo.create_session(
        user_id=user.id,
        token_hash="sha256:absolute",
        csrf_token_hash="sha256:csrf2",
        now=now,
        expires_at=now + timedelta(hours=1),
    )
    assert (
        repo.get_active_session(
            token_hash="sha256:absolute",
            now=now + timedelta(hours=2),
            idle_timeout=timedelta(hours=12),
        )
        is None
    )
    assert absolute.revoked_at is not None


def test_revoke_other_sessions_keeps_current_session_only() -> None:
    session = _make_session()
    user = UserRepository(session).create_user(
        email="member@example.com", display_name="Member"
    )
    repo = HumanAuthRepository(session)
    now = datetime(2026, 8, 11, tzinfo=UTC)
    current = repo.create_session(
        user_id=user.id,
        token_hash="sha256:current",
        csrf_token_hash="sha256:csrf1",
        now=now,
        expires_at=now + timedelta(days=7),
    )
    other = repo.create_session(
        user_id=user.id,
        token_hash="sha256:other",
        csrf_token_hash="sha256:csrf2",
        now=now,
        expires_at=now + timedelta(days=7),
    )

    assert repo.revoke_user_sessions(user.id, except_session_id=current.id) == 1
    assert current.revoked_at is None
    assert other.revoked_at is not None


def test_login_attempt_cleanup_removes_only_expired_rows() -> None:
    session = _make_session()
    repo = HumanAuthRepository(session)
    now = datetime(2026, 8, 11, tzinfo=UTC)
    repo.record_login_attempt(
        email_hash="sha256:old",
        ip_hash="sha256:ip",
        succeeded=False,
        attempted_at=now - timedelta(days=8),
    )
    current = repo.record_login_attempt(
        email_hash="sha256:current",
        ip_hash="sha256:ip",
        succeeded=False,
        attempted_at=now,
    )

    assert repo.delete_login_attempts_before(now - timedelta(days=7)) == 1
    assert session.get(LoginAttempt, current.id) is current


def test_login_rate_limit_is_scoped_to_email_ip_pair_not_email_alone() -> None:
    session = _make_session()
    repo = HumanAuthRepository(session)
    now = datetime(2026, 8, 11, tzinfo=UTC)
    since = now - timedelta(minutes=15)
    for index in range(10):
        repo.record_login_attempt(
            email_hash="sha256:victim",
            ip_hash="sha256:attacker",
            succeeded=False,
            attempted_at=now - timedelta(seconds=index),
        )

    assert (
        repo.is_login_rate_limited(
            email_hash="sha256:victim",
            ip_hash="sha256:attacker",
            since=since,
            max_email_attempts=10,
            max_ip_attempts=30,
        )
        is True
    )
    # Failures from a different network must not lock out the legitimate user.
    assert (
        repo.is_login_rate_limited(
            email_hash="sha256:victim",
            ip_hash="sha256:legit",
            since=since,
            max_email_attempts=10,
            max_ip_attempts=30,
        )
        is False
    )


def test_login_rate_limit_still_enforces_per_ip_ceiling() -> None:
    session = _make_session()
    repo = HumanAuthRepository(session)
    now = datetime(2026, 8, 11, tzinfo=UTC)
    since = now - timedelta(minutes=15)
    for index in range(30):
        repo.record_login_attempt(
            email_hash=f"sha256:account-{index}",
            ip_hash="sha256:spray",
            succeeded=False,
            attempted_at=now - timedelta(seconds=index),
        )

    assert (
        repo.is_login_rate_limited(
            email_hash="sha256:account-new",
            ip_hash="sha256:spray",
            since=since,
            max_email_attempts=10,
            max_ip_attempts=30,
        )
        is True
    )
