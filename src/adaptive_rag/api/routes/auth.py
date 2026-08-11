"""Routes for local users and workspace memberships."""

from __future__ import annotations

import hmac
import logging
from datetime import timedelta
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from adaptive_rag.api.dependencies import (
    SESSION_COOKIE_NAME,
    get_current_user,
    get_session,
    get_workspace_admin_access,
    require_superadmin,
)
from adaptive_rag.api.errors import raise_api_error
from adaptive_rag.api.schemas.auth import (
    AccessTokenRevokeRequestBody,
    AdminUserListResponse,
    AdminUserResponse,
    ChangePasswordRequestBody,
    CsrfTokenResponse,
    CurrentUserPreferencesRequestBody,
    CurrentUserResponse,
    LoginRequestBody,
    SetupRequestBody,
    TemporaryPasswordResponse,
    UserCreateRequestBody,
    UserCreateResponse,
    UserMembershipSummary,
    UserResponse,
    UserUpdateRequestBody,
    WorkspaceMemberAddRequestBody,
    WorkspaceMemberListResponse,
    WorkspaceMemberResponse,
    WorkspaceMembershipListResponse,
    WorkspaceMembershipResponse,
    WorkspaceMembershipUpsertRequestBody,
    WorkspaceMemberUpdateRequestBody,
)
from adaptive_rag.auth import CurrentPrincipal, get_workspace_role, hash_access_token
from adaptive_rag.config.settings import get_settings
from adaptive_rag.db.models import User, WorkspaceMembership
from adaptive_rag.db.models.job import utc_now
from adaptive_rag.db.repositories import (
    HumanAuthRepository,
    UserRepository,
    WorkspaceMembershipRepository,
    WorkspaceRepository,
)
from adaptive_rag.security.human_auth import (
    PasswordService,
    generate_opaque_token,
    generate_temporary_password,
    hash_opaque_secret,
    normalize_email,
)

logger = logging.getLogger(__name__)
_DUMMY_PASSWORD_HASH = PasswordService().hash("invalid credential timing sentinel")

router = APIRouter(tags=["auth"])


@router.post("/auth/setup", response_model=CurrentUserResponse, status_code=201)
def setup_first_superadmin(
    body: SetupRequestBody,
    session: Annotated[Session, Depends(get_session)],
    setup_secret: Annotated[str | None, Header(alias="X-Setup-Secret")] = None,
) -> CurrentUserResponse:
    configured_secret = get_settings().bootstrap_secret
    if (
        configured_secret is None
        or setup_secret is None
        or not hmac.compare_digest(configured_secret.get_secret_value(), setup_secret)
    ):
        raise_api_error(403, "invalid_setup_secret")
    from adaptive_rag.auth import users_exist

    UserRepository(session).lock_bootstrap_creation()
    if users_exist(session):
        raise_api_error(409, "setup_already_complete")
    try:
        user = UserRepository(session).create_user(
            email=body.email,
            display_name=body.display_name,
            system_role="superadmin",
        )
        HumanAuthRepository(session).set_password(
            user_id=user.id,
            password_hash=PasswordService().hash(body.password),
            must_change_password=False,
            password_changed_at=utc_now(),
        )
        session.commit()
    except IntegrityError:
        session.rollback()
        raise_api_error(409, "setup_already_complete")
    except ValueError as exc:
        session.rollback()
        raise_api_error(422, str(exc))
    logger.info("human_auth_setup_completed user_id=%s", user.id)
    return CurrentUserResponse.from_principal(CurrentPrincipal(user=user))


@router.post("/auth/login", response_model=CurrentUserResponse)
def login(
    body: LoginRequestBody,
    request: Request,
    response: Response,
    session: Annotated[Session, Depends(get_session)],
) -> CurrentUserResponse:
    settings = get_settings()
    repo = HumanAuthRepository(session)
    now = utc_now()
    try:
        normalized_email = normalize_email(body.email)
    except ValueError:
        normalized_email = body.email.strip().casefold() or "invalid"
    email_hash = hash_opaque_secret(normalized_email)
    client_ip = request.client.host if request.client is not None else "unknown"
    ip_hash = hash_opaque_secret(client_ip)
    since = now - timedelta(minutes=settings.auth_login_window_minutes)
    # Hold the throttle lock across count, password verify, and attempt insert so
    # concurrent same-bucket logins cannot overshoot configured ceilings.
    repo.lock_login_throttle(email_hash=email_hash, ip_hash=ip_hash)
    if repo.is_login_rate_limited(
        email_hash=email_hash,
        ip_hash=ip_hash,
        since=since,
        max_email_attempts=settings.auth_login_max_attempts_per_email,
        max_ip_attempts=settings.auth_login_max_attempts_per_ip,
    ):
        raise_api_error(429, "rate_limited")

    user = (
        UserRepository(session).get_by_email(normalized_email)
        if "@" in normalized_email
        else None
    )
    credential = repo.get_credential(user.id) if user is not None else None
    encoded_hash = (
        credential.password_hash if credential is not None else _DUMMY_PASSWORD_HASH
    )
    password_valid = PasswordService().verify(encoded_hash, body.password)
    authenticated = bool(user is not None and user.is_active and password_valid)
    repo.record_login_attempt(
        email_hash=email_hash,
        ip_hash=ip_hash,
        succeeded=authenticated,
        attempted_at=now,
    )
    repo.delete_login_attempts_before(
        now - timedelta(days=settings.auth_login_attempt_retention_days)
    )
    if not authenticated or user is None or credential is None:
        session.commit()
        raise_api_error(401, "invalid_credentials")

    password_service = PasswordService()
    if password_service.needs_rehash(credential.password_hash):
        credential.password_hash = password_service.hash(body.password)
    raw_session_token = generate_opaque_token()
    raw_csrf_token = generate_opaque_token()
    human_session = repo.create_session(
        user_id=user.id,
        token_hash=hash_opaque_secret(raw_session_token),
        csrf_token_hash=hash_opaque_secret(raw_csrf_token),
        now=now,
        expires_at=now + timedelta(days=settings.auth_session_absolute_days),
    )
    session.commit()
    secure_cookie = (
        settings.auth_cookie_secure
        if settings.auth_cookie_secure is not None
        else settings.env not in {"local", "test"}
    )
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=raw_session_token,
        httponly=True,
        secure=secure_cookie,
        samesite="lax",
        path="/",
        max_age=settings.auth_session_absolute_days * 24 * 60 * 60,
    )
    response.headers["Cache-Control"] = "no-store"
    return CurrentUserResponse.from_principal(
        CurrentPrincipal(
            user=user,
            auth_method="session",
            session_id=human_session.id,
            csrf_token_hash=human_session.csrf_token_hash,
            must_change_password=credential.must_change_password,
        )
    )


@router.get("/auth/csrf", response_model=CsrfTokenResponse)
def get_csrf_token(
    response: Response,
    session: Annotated[Session, Depends(get_session)],
    current: Annotated[CurrentPrincipal, Depends(get_current_user)],
) -> CsrfTokenResponse:
    if current.auth_method != "session" or current.session_id is None:
        raise_api_error(400, "session_required")
    raw_token = generate_opaque_token()
    if not HumanAuthRepository(session).rotate_csrf_token(
        current.session_id, csrf_token_hash=hash_opaque_secret(raw_token)
    ):
        raise_api_error(401, "authentication_required")
    session.commit()
    response.headers["Cache-Control"] = "no-store"
    return CsrfTokenResponse(csrf_token=raw_token)


@router.post("/auth/change-password", response_model=CurrentUserResponse)
def change_password(
    body: ChangePasswordRequestBody,
    session: Annotated[Session, Depends(get_session)],
    current: Annotated[CurrentPrincipal, Depends(get_current_user)],
) -> CurrentUserResponse:
    if current.user is None or current.session_id is None:
        raise_api_error(400, "session_required")
    repo = HumanAuthRepository(session)
    credential = repo.get_credential(current.user.id)
    if credential is None:
        raise_api_error(409, "password_credential_missing")
    password_service = PasswordService()
    if not credential.must_change_password and (
        body.current_password is None
        or not password_service.verify(credential.password_hash, body.current_password)
    ):
        raise_api_error(401, "invalid_credentials")
    try:
        repo.set_password(
            user_id=current.user.id,
            password_hash=password_service.hash(body.new_password),
            must_change_password=False,
            password_changed_at=utc_now(),
        )
    except IntegrityError:
        session.rollback()
        raise_api_error(409, "email_already_exists")
    except ValueError as exc:
        raise_api_error(422, str(exc))
    repo.revoke_user_sessions(current.user.id, except_session_id=current.session_id)
    session.commit()
    return CurrentUserResponse.from_principal(
        CurrentPrincipal(
            user=current.user,
            auth_method="session",
            session_id=current.session_id,
            must_change_password=False,
        )
    )


@router.post("/auth/logout", status_code=204)
def logout(
    response: Response,
    session: Annotated[Session, Depends(get_session)],
    current: Annotated[CurrentPrincipal, Depends(get_current_user)],
) -> None:
    if current.session_id is not None:
        HumanAuthRepository(session).revoke_session(current.session_id)
        session.commit()
    response.delete_cookie(SESSION_COOKIE_NAME, path="/")
    response.headers["Cache-Control"] = "no-store"


@router.get("/auth/me", response_model=CurrentUserResponse)
def get_me(
    response: Response,
    current: Annotated[CurrentPrincipal, Depends(get_current_user)],
) -> CurrentUserResponse:
    response.headers["Cache-Control"] = "no-store"
    return CurrentUserResponse.from_principal(current)


@router.patch("/auth/me/preferences", response_model=CurrentUserResponse)
def update_me_preferences(
    body: CurrentUserPreferencesRequestBody,
    session: Annotated[Session, Depends(get_session)],
    current: Annotated[CurrentPrincipal, Depends(get_current_user)],
) -> CurrentUserResponse:
    if current.user_id is None:
        raise_api_error(401, "authentication_required")

    if body.last_workspace_id is not None:
        if WorkspaceRepository(session).get(body.last_workspace_id) is None:
            raise_api_error(404, "workspace_not_found")
        if (
            get_workspace_role(
                session,
                principal=current,
                workspace_id=body.last_workspace_id,
            )
            is None
        ):
            raise_api_error(403, "workspace_access_required")

    user = UserRepository(session).update_last_workspace_id(
        current.user_id,
        last_workspace_id=body.last_workspace_id,
    )
    if user is None:
        raise_api_error(404, "user_not_found")
    session.commit()
    return CurrentUserResponse.from_principal(CurrentPrincipal(user=user))


@router.get("/admin/users", response_model=AdminUserListResponse)
def list_users(
    session: Annotated[Session, Depends(get_session)],
    current: Annotated[CurrentPrincipal, Depends(get_current_user)],
    q: str | None = None,
    status: Literal["active", "suspended"] | None = None,
) -> AdminUserListResponse:
    require_superadmin(current)
    users = UserRepository(session).list_users()
    if q is not None and q.strip():
        needle = q.strip().casefold()
        users = [
            user
            for user in users
            if needle in user.email.casefold() or needle in user.display_name.casefold()
        ]
    if status is not None:
        active = status == "active"
        users = [user for user in users if user.is_active is active]
    return AdminUserListResponse(
        items=[_admin_user_response(session, user) for user in users]
    )


@router.post("/admin/users", response_model=UserCreateResponse, status_code=201)
def create_user(
    body: UserCreateRequestBody,
    response: Response,
    session: Annotated[Session, Depends(get_session)],
    current: Annotated[CurrentPrincipal, Depends(get_current_user)],
) -> UserCreateResponse:
    require_superadmin(current)
    if body.system_role == "user" and (
        body.initial_workspace_id is None or body.initial_workspace_role is None
    ):
        raise_api_error(422, "initial_membership_required")
    if body.system_role == "superadmin" and (
        body.initial_workspace_id is not None or body.initial_workspace_role is not None
    ):
        raise_api_error(422, "superadmin_membership_forbidden")
    if (
        body.initial_workspace_id is not None
        and WorkspaceRepository(session).get(body.initial_workspace_id) is None
    ):
        raise_api_error(404, "workspace_not_found")
    temporary_password = generate_temporary_password()
    try:
        repo = UserRepository(session)
        user = repo.create_user(
            email=body.email,
            display_name=body.display_name,
            system_role=body.system_role,
        )
        HumanAuthRepository(session).set_password(
            user_id=user.id,
            password_hash=PasswordService().hash(temporary_password),
            must_change_password=True,
        )
        if (
            body.initial_workspace_id is not None
            and body.initial_workspace_role is not None
        ):
            WorkspaceMembershipRepository(session).upsert_membership(
                workspace_id=body.initial_workspace_id,
                user_id=user.id,
                role=body.initial_workspace_role,
            )
    except ValueError as exc:
        session.rollback()
        detail = str(exc)
        status_code = 409 if detail == "email_already_exists" else 422
        raise_api_error(status_code, detail)
    session.commit()
    response.headers["Cache-Control"] = "no-store"
    logger.info(
        "admin_user_created actor_id=%s target_id=%s system_role=%s",
        current.user_id,
        user.id,
        user.system_role,
    )
    return UserCreateResponse(
        user=_admin_user_response(session, user),
        temporary_password=temporary_password,
    )


@router.patch("/admin/users/{user_id}", response_model=AdminUserResponse)
def update_user(
    user_id: UUID,
    body: UserUpdateRequestBody,
    session: Annotated[Session, Depends(get_session)],
    current: Annotated[CurrentPrincipal, Depends(get_current_user)],
) -> AdminUserResponse:
    require_superadmin(current)
    repo = UserRepository(session)
    target = repo.get_user(user_id)
    if target is None:
        raise_api_error(404, "user_not_found")
    if target.system_role == "superadmin" and body.system_role == "user":
        repo.lock_superadmin_invariant()
        target = repo.get_user_for_update(user_id)
        if target is None:
            raise_api_error(404, "user_not_found")
        if (
            target.system_role == "superadmin"
            and target.is_active
            and len(repo.list_active_superadmins_for_update()) <= 1
        ):
            raise_api_error(409, "last_active_superadmin")
    else:
        target = repo.get_user_for_update(user_id)
        if target is None:
            raise_api_error(404, "user_not_found")
    try:
        updated = repo.update_user(
            user_id,
            email=body.email,
            display_name=body.display_name,
            system_role=body.system_role,
        )
    except IntegrityError:
        session.rollback()
        raise_api_error(409, "email_already_exists")
    except ValueError as exc:
        session.rollback()
        code = str(exc)
        raise_api_error(409 if code == "email_already_exists" else 422, code)
    if updated is None:
        raise_api_error(404, "user_not_found")
    session.commit()
    logger.info("admin_user_updated actor_id=%s target_id=%s", current.user_id, user_id)
    return _admin_user_response(session, updated)


@router.get(
    "/workspaces/{workspace_id}/memberships",
    response_model=WorkspaceMembershipListResponse,
)
def list_workspace_memberships(
    workspace_id: UUID,
    session: Annotated[Session, Depends(get_session)],
    _access: Annotated[tuple[object, str], Depends(get_workspace_admin_access)],
) -> WorkspaceMembershipListResponse:
    memberships = WorkspaceMembershipRepository(session).list_workspace_members(
        workspace_id=workspace_id
    )
    return WorkspaceMembershipListResponse.from_memberships(memberships)


@router.get(
    "/workspaces/{workspace_id}/members",
    response_model=WorkspaceMemberListResponse,
)
def list_workspace_members(
    workspace_id: UUID,
    session: Annotated[Session, Depends(get_session)],
    _access: Annotated[tuple[object, str], Depends(get_workspace_admin_access)],
) -> WorkspaceMemberListResponse:
    memberships = WorkspaceMembershipRepository(session).list_workspace_members(
        workspace_id
    )
    return WorkspaceMemberListResponse(
        items=[_workspace_member_response(session, item) for item in memberships]
    )


@router.post(
    "/workspaces/{workspace_id}/members",
    response_model=WorkspaceMemberResponse,
    status_code=201,
)
def add_workspace_member(
    workspace_id: UUID,
    body: WorkspaceMemberAddRequestBody,
    session: Annotated[Session, Depends(get_session)],
    current: Annotated[CurrentPrincipal, Depends(get_current_user)],
    _access: Annotated[tuple[object, str], Depends(get_workspace_admin_access)],
) -> WorkspaceMemberResponse:
    try:
        user = UserRepository(session).get_by_email(body.email)
    except ValueError:
        user = None
    if user is None:
        raise_api_error(404, "user_not_found")
    if (
        WorkspaceMembershipRepository(session).get_membership(
            workspace_id=workspace_id, user_id=user.id
        )
        is not None
    ):
        raise_api_error(409, "membership_already_exists")
    try:
        membership = WorkspaceMembershipRepository(session).upsert_membership(
            workspace_id=workspace_id, user_id=user.id, role=body.role
        )
    except IntegrityError:
        session.rollback()
        raise_api_error(409, "membership_already_exists")
    session.commit()
    logger.info(
        "workspace_member_added actor_id=%s target_id=%s workspace_id=%s role=%s",
        current.user_id,
        user.id,
        workspace_id,
        body.role,
    )
    return _workspace_member_response(session, membership)


@router.patch(
    "/workspaces/{workspace_id}/members/{user_id}",
    response_model=WorkspaceMemberResponse,
)
def update_workspace_member(
    workspace_id: UUID,
    user_id: UUID,
    body: WorkspaceMemberUpdateRequestBody,
    session: Annotated[Session, Depends(get_session)],
    current: Annotated[CurrentPrincipal, Depends(get_current_user)],
    _access: Annotated[tuple[object, str], Depends(get_workspace_admin_access)],
) -> WorkspaceMemberResponse:
    WorkspaceRepository(session).get_for_update(workspace_id)
    repo = WorkspaceMembershipRepository(session)
    active_admins = repo.list_active_workspace_admins_for_update(workspace_id)
    membership = repo.get_membership_for_update(
        workspace_id=workspace_id, user_id=user_id
    )
    if membership is None:
        raise_api_error(404, "membership_not_found")
    target = UserRepository(session).get_user(user_id)
    if (
        membership.role == "admin"
        and body.role != "admin"
        and target is not None
        and target.is_active
        and len(active_admins) <= 1
    ):
        raise_api_error(409, "last_active_workspace_admin")
    membership = repo.upsert_membership(
        workspace_id=workspace_id, user_id=user_id, role=body.role
    )
    session.commit()
    logger.info(
        "workspace_member_role_changed actor_id=%s target_id=%s "
        "workspace_id=%s role=%s",
        current.user_id,
        user_id,
        workspace_id,
        body.role,
    )
    return _workspace_member_response(session, membership)


@router.delete(
    "/workspaces/{workspace_id}/members/{user_id}",
    status_code=204,
)
def remove_workspace_member(
    workspace_id: UUID,
    user_id: UUID,
    session: Annotated[Session, Depends(get_session)],
    current: Annotated[CurrentPrincipal, Depends(get_current_user)],
    _access: Annotated[tuple[object, str], Depends(get_workspace_admin_access)],
) -> None:
    WorkspaceRepository(session).get_for_update(workspace_id)
    repo = WorkspaceMembershipRepository(session)
    active_admins = repo.list_active_workspace_admins_for_update(workspace_id)
    membership = repo.get_membership_for_update(
        workspace_id=workspace_id, user_id=user_id
    )
    if membership is None:
        raise_api_error(404, "membership_not_found")
    target = UserRepository(session).get_user(user_id)
    if (
        membership.role == "admin"
        and target is not None
        and target.is_active
        and len(active_admins) <= 1
    ):
        raise_api_error(409, "last_active_workspace_admin")
    session.delete(membership)
    session.commit()
    logger.info(
        "workspace_member_removed actor_id=%s target_id=%s workspace_id=%s",
        current.user_id,
        user_id,
        workspace_id,
    )


@router.put(
    "/workspaces/{workspace_id}/memberships/{user_id}",
    response_model=WorkspaceMembershipResponse,
)
def upsert_workspace_membership(
    workspace_id: UUID,
    user_id: UUID,
    body: WorkspaceMembershipUpsertRequestBody,
    session: Annotated[Session, Depends(get_session)],
    current: Annotated[CurrentPrincipal, Depends(get_current_user)],
    _access: Annotated[tuple[object, str], Depends(get_workspace_admin_access)],
) -> WorkspaceMembershipResponse:
    """Legacy membership upsert; keeps the same last-admin invariant as /members."""

    WorkspaceRepository(session).get_for_update(workspace_id)
    repo = WorkspaceMembershipRepository(session)
    active_admins = repo.list_active_workspace_admins_for_update(workspace_id)
    existing = repo.get_membership_for_update(
        workspace_id=workspace_id, user_id=user_id
    )
    target = UserRepository(session).get_user(user_id)
    if target is None:
        raise_api_error(404, "user_not_found")
    if (
        existing is not None
        and existing.role == "admin"
        and body.role != "admin"
        and target.is_active
        and len(active_admins) <= 1
    ):
        raise_api_error(409, "last_active_workspace_admin")
    try:
        membership = repo.upsert_membership(
            workspace_id=workspace_id,
            user_id=user_id,
            role=body.role,
        )
    except ValueError as exc:
        raise_api_error(422, str(exc))
    session.commit()
    logger.info(
        "workspace_membership_upserted actor_id=%s target_id=%s "
        "workspace_id=%s role=%s",
        current.user_id,
        user_id,
        workspace_id,
        body.role,
    )
    return WorkspaceMembershipResponse.from_membership(membership)


@router.delete(
    "/workspaces/{workspace_id}/memberships/{user_id}",
    status_code=204,
)
def delete_workspace_membership(
    workspace_id: UUID,
    user_id: UUID,
    session: Annotated[Session, Depends(get_session)],
    current: Annotated[CurrentPrincipal, Depends(get_current_user)],
    _access: Annotated[tuple[object, str], Depends(get_workspace_admin_access)],
) -> None:
    """Legacy membership delete; keeps the same last-admin invariant as /members."""

    WorkspaceRepository(session).get_for_update(workspace_id)
    repo = WorkspaceMembershipRepository(session)
    active_admins = repo.list_active_workspace_admins_for_update(workspace_id)
    membership = repo.get_membership_for_update(
        workspace_id=workspace_id, user_id=user_id
    )
    if membership is None:
        raise_api_error(404, "membership_not_found")
    target = UserRepository(session).get_user(user_id)
    if (
        membership.role == "admin"
        and target is not None
        and target.is_active
        and len(active_admins) <= 1
    ):
        raise_api_error(409, "last_active_workspace_admin")
    session.delete(membership)
    session.commit()
    logger.info(
        "workspace_membership_deleted actor_id=%s target_id=%s workspace_id=%s",
        current.user_id,
        user_id,
        workspace_id,
    )


@router.post("/admin/users/{user_id}/suspend", response_model=AdminUserResponse)
@router.post("/admin/users/{user_id}/deactivate", response_model=AdminUserResponse)
def suspend_user(
    user_id: UUID,
    session: Annotated[Session, Depends(get_session)],
    current: Annotated[CurrentPrincipal, Depends(get_current_user)],
) -> AdminUserResponse:
    require_superadmin(current)
    user_repo = UserRepository(session)
    target = user_repo.get_user(user_id)
    if target is None:
        raise_api_error(404, "user_not_found")
    if not target.is_active:
        return _admin_user_response(session, target)
    if target.system_role == "superadmin":
        user_repo.lock_superadmin_invariant()
        active_superadmins = user_repo.list_active_superadmins_for_update()
        target = user_repo.get_user_for_update(user_id)
        if target is None:
            raise_api_error(404, "user_not_found")
        if not target.is_active:
            return _admin_user_response(session, target)
        if len(active_superadmins) <= 1:
            raise_api_error(409, "last_active_superadmin")
    else:
        target = user_repo.get_user_for_update(user_id)
        if target is None:
            raise_api_error(404, "user_not_found")
        if not target.is_active:
            return _admin_user_response(session, target)
    memberships = WorkspaceMembershipRepository(session).list_user_memberships(user_id)
    admin_workspace_ids = sorted(
        (item.workspace_id for item in memberships if item.role == "admin"), key=str
    )
    for workspace_id in admin_workspace_ids:
        WorkspaceRepository(session).get_for_update(workspace_id)
        active_admins = WorkspaceMembershipRepository(
            session
        ).list_active_workspace_admins_for_update(workspace_id)
        if len(active_admins) <= 1:
            raise_api_error(409, "last_active_workspace_admin")
    user = user_repo.update_user(user_id, is_active=False)
    if user is None:
        raise_api_error(404, "user_not_found")
    HumanAuthRepository(session).revoke_user_sessions(user_id)
    session.commit()
    logger.info(
        "admin_user_suspended actor_id=%s target_id=%s", current.user_id, user_id
    )
    return _admin_user_response(session, user)


@router.post("/admin/users/{user_id}/reactivate", response_model=AdminUserResponse)
def reactivate_user(
    user_id: UUID,
    session: Annotated[Session, Depends(get_session)],
    current: Annotated[CurrentPrincipal, Depends(get_current_user)],
) -> AdminUserResponse:
    require_superadmin(current)
    repo = UserRepository(session)
    if repo.get_user_for_update(user_id) is None:
        raise_api_error(404, "user_not_found")
    user = repo.update_user(user_id, is_active=True)
    if user is None:  # defensive: the locked row cannot disappear in-transaction
        raise_api_error(404, "user_not_found")
    session.commit()
    logger.info(
        "admin_user_reactivated actor_id=%s target_id=%s", current.user_id, user_id
    )
    return _admin_user_response(session, user)


@router.post(
    "/admin/users/{user_id}/reset-password",
    response_model=TemporaryPasswordResponse,
)
def reset_user_password(
    user_id: UUID,
    response: Response,
    session: Annotated[Session, Depends(get_session)],
    current: Annotated[CurrentPrincipal, Depends(get_current_user)],
) -> TemporaryPasswordResponse:
    require_superadmin(current)
    user = UserRepository(session).get_user_for_update(user_id)
    if user is None:
        raise_api_error(404, "user_not_found")
    temporary_password = generate_temporary_password()
    HumanAuthRepository(session).set_password(
        user_id=user_id,
        password_hash=PasswordService().hash(temporary_password),
        must_change_password=True,
    )
    HumanAuthRepository(session).revoke_user_sessions(user_id)
    session.commit()
    response.headers["Cache-Control"] = "no-store"
    logger.info(
        "admin_password_reset actor_id=%s target_id=%s", current.user_id, user_id
    )
    return TemporaryPasswordResponse(
        user=_admin_user_response(session, user),
        temporary_password=temporary_password,
    )


def _admin_user_response(session: Session, user: User) -> AdminUserResponse:
    credential = HumanAuthRepository(session).get_credential(user.id)
    memberships: list[UserMembershipSummary] = []
    for membership in WorkspaceMembershipRepository(session).list_user_memberships(
        user.id
    ):
        workspace = WorkspaceRepository(session).get(membership.workspace_id)
        memberships.append(
            UserMembershipSummary(
                workspace_id=membership.workspace_id,
                workspace_name=(
                    workspace.name if workspace is not None else "Deleted workspace"
                ),
                role=membership.role,  # type: ignore[arg-type]
            )
        )
    base = UserResponse.from_user(user)
    return AdminUserResponse(
        **base.model_dump(),
        must_change_password=(
            credential.must_change_password if credential is not None else False
        ),
        memberships=memberships,
    )


def _workspace_member_response(
    session: Session, membership: WorkspaceMembership
) -> WorkspaceMemberResponse:
    user = UserRepository(session).get_user(membership.user_id)
    if user is None:
        raise_api_error(409, "membership_user_missing")
    return WorkspaceMemberResponse(
        id=membership.id,
        workspace_id=membership.workspace_id,
        user_id=membership.user_id,
        email=user.email,
        display_name=user.display_name,
        is_active=user.is_active,
        role=membership.role,  # type: ignore[arg-type]
        created_at=membership.created_at,
        updated_at=membership.updated_at,
    )


@router.post("/admin/access-tokens/revoke")
def revoke_access_token(
    body: AccessTokenRevokeRequestBody,
    session: Annotated[Session, Depends(get_session)],
    current: Annotated[CurrentPrincipal, Depends(get_current_user)],
) -> dict[str, bool]:
    require_superadmin(current)
    if not body.access_token.strip():
        raise HTTPException(status_code=422, detail="access_token is required")
    revoked = UserRepository(session).revoke_access_token(
        hash_access_token(body.access_token)
    )
    if not revoked:
        raise HTTPException(status_code=404, detail="access token not found")
    session.commit()
    return {"revoked": True}
