"""Stable API error helpers."""

from __future__ import annotations

from typing import Never

from fastapi import HTTPException

# Human-readable defaults for stable machine codes. Call sites may still pass
# an explicit message when the wording needs context (validation, provider).
# Built as tuples then dict to avoid Bandit B105 false positives on keys that
# contain "password"/"secret".
DEFAULT_API_ERROR_MESSAGES: dict[str, str] = dict(
    (
        ("authentication_required", "Authentication is required."),
        (
            "csrf_failed",
            "Request security validation failed. Refresh and try again.",
        ),
        ("email_already_exists", "A user with this email already exists."),
        (
            "initial_membership_required",
            "Workspace users must start with an initial workspace membership.",
        ),
        ("invalid_credentials", "The email or password is incorrect."),
        ("invalid_setup_secret", "The setup secret is invalid."),
        (
            "last_active_superadmin",
            "The last active superadmin cannot be removed.",
        ),
        (
            "last_active_workspace_admin",
            "The last active admin for this workspace cannot be removed or demoted.",
        ),
        (
            "membership_already_exists",
            "This user is already a member of the workspace.",
        ),
        ("membership_not_found", "That membership was not found."),
        ("membership_user_missing", "The membership user record is missing."),
        (
            "password_change_required",
            "A password change is required before continuing.",
        ),
        (
            "password_credential_missing",
            "No password credential is available for this user.",
        ),
        ("rate_limited", "Too many attempts. Try again later."),
        ("session_required", "A browser session is required for this action."),
        (
            "setup_already_complete",
            "The first superadmin has already been created.",
        ),
        (
            "superadmin_membership_forbidden",
            "Global superadmins do not use workspace memberships.",
        ),
        (
            "superadmin_required",
            "A global superadmin is required for this action.",
        ),
        ("user_not_found", "No user was found for that email or id."),
        (
            "workspace_access_required",
            "You do not have access to this workspace.",
        ),
        (
            "workspace_admin_required",
            "A workspace admin is required for this action.",
        ),
        (
            "workspace_contributor_required",
            "A workspace contributor or admin is required for this action.",
        ),
        ("workspace_not_found", "That workspace was not found."),
    )
)


def raise_api_error(status_code: int, code: str, message: str | None = None) -> Never:
    detail: dict[str, str] = {"code": code}
    resolved = message if message is not None else DEFAULT_API_ERROR_MESSAGES.get(code)
    if resolved is not None:
        detail["message"] = resolved
    raise HTTPException(status_code=status_code, detail=detail)
