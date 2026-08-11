"""Explicit compatibility auth for pre-human-auth API integration tests.

These tests historically exercised unrelated endpoints through the removed
empty-database bootstrap path. Keeping that behavior as a test-only dependency
override lets production authentication remain fail-closed.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import FastAPI, Header, HTTPException
from sqlalchemy.orm import Session

from adaptive_rag.api.dependencies import get_current_user
from adaptive_rag.auth import CurrentPrincipal, hash_access_token, users_exist
from adaptive_rag.db.repositories import UserRepository


def install_legacy_auth_override(app: FastAPI, session: Session) -> None:
    def resolve_test_principal(
        authorization: Annotated[str | None, Header()] = None,
    ) -> CurrentPrincipal:
        if authorization is None or not authorization.strip():
            if users_exist(session):
                raise HTTPException(status_code=401, detail="authentication required")
            return CurrentPrincipal(
                user=None, is_bootstrap=True, auth_method="bootstrap"
            )
        scheme, separator, token = authorization.partition(" ")
        if separator == "" or scheme.casefold() != "bearer" or not token.strip():
            raise HTTPException(status_code=401, detail="invalid authorization header")
        user = UserRepository(session).get_user_by_token_hash(
            hash_access_token(token)
        )
        if user is None:
            raise HTTPException(status_code=401, detail="invalid access token")
        if not user.is_active:
            raise HTTPException(status_code=401, detail="inactive_user")
        return CurrentPrincipal(user=user, auth_method="bearer")

    app.dependency_overrides[get_current_user] = resolve_test_principal
