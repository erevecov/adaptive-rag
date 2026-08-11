# Multi-Workspace User Management Design

**Date:** 2026-08-11

**Status:** Approved design, pending written-spec review

## Goal

Add complete human user management to Adaptive RAG while preserving its existing
multi-workspace RBAC foundation. Human users authenticate with a local email and
password. Global superadmins manage identities and all workspaces, while
workspace roles remain independent memberships that can differ for the same user
across workspaces.

## Context

Adaptive RAG already has most of the authorization foundation:

- global `User` identities with `system_role = "user" | "superadmin"`;
- hash-only bearer tokens;
- `WorkspaceMembership` rows with `viewer`, `contributor`, and `admin`;
- backend dependencies that enforce workspace role thresholds;
- global user and workspace-membership endpoints;
- an initial combined Users/Memberships frontend panel.

The current surface is not yet suitable for human user management. The browser
authenticates with a configured bearer token, user creation accepts manually
entered tokens, workspace admins cannot discover an existing user without a UUID,
and the frontend mixes global identity actions with workspace membership actions.

BeFlow provides useful interaction patterns for a user directory: search,
status filters, responsive table/cards, row actions, destructive confirmations,
and explicit success/error feedback. Its roles are global, however, so Adaptive
RAG must retain a separate global-identity and workspace-membership model.

## Scope

This change includes:

- local human authentication with email, password, and server-side sessions;
- first-login mandatory password change;
- one-time temporary password generation and copy UI;
- global user administration for superadmins;
- workspace-scoped member administration for workspace admins;
- role-aware navigation and actions;
- safe migration from the current bearer-token-only browser flow;
- lifecycle and concurrency protections for the last active superadmin and last
  workspace admin;
- backend, frontend, migration, security, and end-to-end verification.

## Out of Scope

- email invitations or email-based password recovery;
- SSO, OAuth, OIDC, Supabase Auth, Clerk, Auth0, or another external identity
  provider;
- MFA;
- hard deletion of users;
- custom roles or arbitrary permissions;
- an API-key management UI or automatic API-key rotation;
- bulk cross-workspace membership changes;
- periodic forced password rotation.

## Domain Model

### Global user identity

`User` remains the global identity and authorization subject. Its relevant fields
are:

- `id`;
- `email`, unique after trimming and lowercasing;
- `display_name`;
- `system_role = "user" | "superadmin"`;
- `is_active`;
- `last_workspace_id`;
- timestamps.

The current `login` field is renamed to `email` in the model, database, API, and
frontend contracts. Email is the canonical login identifier even though the
system does not send email in this version.

`superadmin` is only a global system role. `viewer`, `contributor`, and `admin`
must never be stored in `User.system_role`.

### Workspace membership

`WorkspaceMembership` remains the only source of workspace-scoped roles:

- `workspace_id`;
- `user_id`;
- `role = "viewer" | "contributor" | "admin"`;
- timestamps;
- a uniqueness constraint on `(workspace_id, user_id)`.

A user can have any number of workspace memberships and a different role in each
workspace. For example, the same identity can be `viewer` in workspace 1 and
`admin` in workspace 2. Changing one membership must not change any other
membership.

### Password credential

Human password data lives in a separate one-to-one credential table so a future
external identity provider can replace local password verification without
changing the user or membership model.

`UserPasswordCredential` contains:

- `user_id`, primary key and foreign key to `users.id`;
- `password_hash`;
- `must_change_password`;
- `password_changed_at`;
- timestamps.

Plaintext passwords are never persisted. Passwords use Argon2id with at least
19 MiB memory, two iterations, and parallelism one. The password service owns
hashing and verification; routes and repositories never implement hashing
directly.

### Human session

`UserSession` contains:

- `id`;
- `user_id`;
- a unique SHA-256 hash of a 32-byte random session token;
- a hash of the session-bound CSRF token;
- `last_seen_at`;
- `expires_at` for the seven-day absolute limit;
- `revoked_at`;
- timestamps.

The raw session token exists only in the browser cookie and the login response
processing path. Session lookup must reject revoked, idle-expired, absolute-
expired, inactive-user, and missing-user sessions.

### Technical bearer tokens

The existing `UserAccessToken` rows remain hash-only technical credentials for
CLI, MCP, scripts, and integrations. They are not used by the human login or user
creation UI. The authentication adapter accepts a human session cookie first and
then an `Authorization: Bearer` credential for technical clients.

Bearer-token issuance, rotation, and UI management are outside this change.

## Role and Permission Model

Roles are cumulative within a workspace:

| Effective role | Permissions |
| --- | --- |
| `viewer` | Use workspace chat and retrieval/RAG and read the user's own chat history. |
| `contributor` | All viewer permissions plus create, edit, sync, and ingest knowledge and review knowledge proposals. |
| `admin` | All contributor permissions plus update the workspace, its workspace-level settings, and its members. |
| `superadmin` | All permissions in every workspace plus global identities, workspace creation/lifecycle, global runtime, provider, and system administration. |

An effective workspace role is calculated from the current principal and the
target workspace. A superadmin resolves to `superadmin` without a membership row.
An ordinary user resolves only through that workspace's membership. No role from
one workspace can authorize an operation in another workspace.

### Global user administration

Only a superadmin can:

- create an identity;
- list or search the global user directory;
- inspect all memberships for a user;
- update a user's email or display name;
- promote a user to superadmin or demote a superadmin to an ordinary user;
- suspend or reactivate an identity;
- reset a password;
- manage memberships in any workspace.

Creating an ordinary user requires one initial `(workspace_id, role)` assignment.
The identity, password credential, and membership are created atomically. Creating
a superadmin forbids an initial workspace membership because its authority is
global. Additional memberships can be added later to an ordinary user.

Promoting an ordinary user to superadmin retains existing memberships but makes
global authority effective. Demoting a superadmin restores the retained
workspace-scoped memberships. A global-role update that would leave zero active
superadmins fails.

### Workspace member administration

A workspace admin:

- lists only users who are members of that workspace;
- adds an existing global user by exact email;
- assigns `viewer`, `contributor`, or `admin`;
- changes or removes memberships only in that workspace;
- cannot list or search the global directory;
- cannot create, suspend, reactivate, rename, reset, promote to superadmin, or
  otherwise mutate a global identity.

Exact-email addition returns the generic `user_not_found_or_not_addable` error
when the identity does not exist or cannot be added. It never provides a fuzzy or
prefix-based global search surface.

### Last-administrator invariants

The system must always retain at least one active superadmin. It rejects:

- self-suspension by a superadmin;
- suspension or demotion of the last active superadmin;
- concurrent changes that would jointly leave zero active superadmins.

Each active workspace must retain at least one active admin membership. It rejects
removal or demotion of the last active workspace admin. A replacement can be
assigned in the same transaction before the previous admin is removed or
demoted. Superadmins use the same invariant and cannot leave an active workspace
without an admin accidentally.

The service layer enforces these rules inside database transactions with row
locks. Frontend guards are convenience only and are not authorization controls.

## Authentication Flows

### Bootstrap

When no user exists, all protected application endpoints return
`setup_required`. The only identity mutation available is:

`POST /setup/superadmin`

The request requires the `ADAPTIVE_RAG_BOOTSTRAP_SECRET` value in the
`X-Setup-Secret` header and accepts the first superadmin's email and display name. The service
compares the secret in constant time, creates the identity and password
credential, and returns a generated temporary password once. The endpoint becomes
unavailable as soon as any user exists.

The current behavior that treats an empty user table as an unrestricted
superadmin principal is removed.

### Login

`POST /auth/login` accepts normalized email and password. Both an unknown email
and a wrong password return `invalid_credentials`. The route does not expose
whether an identity exists, is suspended, or lacks a password credential.

On success the service creates a random session and CSRF token, persists only
their hashes, sets the session cookie, and returns the current-user payload plus
the raw CSRF token for in-memory use by the SPA. Authentication and one-time
credential responses use `Cache-Control: no-store`.

The session cookie is named `adaptive_rag_session` and uses:

- `HttpOnly`;
- `SameSite=Lax`;
- `Secure` outside local development;
- path `/`;
- no JavaScript-readable value.

Cookie-authenticated unsafe requests require both an allowed `Origin` and an
`X-CSRF-Token` header that matches the session-bound token. Bearer-authenticated
technical requests do not use browser cookies and are exempt from CSRF checks.

After a page reload, `GET /auth/csrf` rotates the session-bound CSRF token,
persists its new hash, and returns the raw replacement for in-memory use. CORS
prevents another origin from reading that response.

Login attempts are rate-limited to ten failures per normalized email and thirty
failures per client IP within a rolling 15-minute window. Counters are server-side,
survive multiple application processes, and use the same generic login response
when throttled. A successful login clears the email counter.

### Mandatory first password change

A user with `must_change_password = true` can only call:

- `GET /auth/me`;
- `GET /auth/csrf`;
- `POST /auth/change-password`;
- `POST /auth/logout`.

All other protected routes return `password_change_required`. The frontend routes
the user to a blocking password-change view. A successful change stores a new
Argon2id hash, clears `must_change_password`, updates `password_changed_at`, and
rotates the current session.

This restriction applies to human cookie sessions. A separately issued technical
bearer token remains an independent authenticator and does not require an
interactive password-change flow.

User-selected passwords must:

- contain 15 to 128 Unicode code points;
- permit spaces and paste/password-manager input;
- not use composition rules;
- not require periodic rotation.

### Logout and expiry

`POST /auth/logout` revokes the current session and clears its cookie. Sessions
expire after 12 hours without activity and after seven days absolutely. The
server rejects expired sessions even if the browser still holds a cookie.

### Administrative reset

A superadmin can reset any user's password, including their own. Reset:

- generates a new 32-byte random URL-safe temporary password;
- replaces the Argon2id hash;
- sets `must_change_password = true`;
- revokes all of the target user's sessions;
- returns the plaintext temporary password once.

Resetting a password does not change memberships, global role, or active state.

## User Lifecycle

Suspension is reversible and global. Suspending a user sets `is_active = false`
and revokes all human sessions. It preserves password credentials, workspace
memberships, chat ownership, and audit history.

Before suspension, the service checks every active workspace where the target is
an admin. It rejects the operation with `last_workspace_admin` and the affected
workspace IDs if suspension would leave any active workspace without an active
admin membership. Replacements must be assigned first.

Reactivation sets `is_active = true`. It does not create a new password or
session. If compromise is suspected, the superadmin performs reset-password as a
separate explicit action.

Email changes normalize and uniqueness-check the new value and revoke all human
sessions. Display-name changes do not revoke sessions. Hard deletion is not
available.

Removing a workspace member deletes only that `WorkspaceMembership`; it never
suspends or mutates the global user.

## API Contracts

### Human auth

- `POST /auth/login`
- `GET /auth/me`
- `GET /auth/csrf`
- `POST /auth/change-password`
- `POST /auth/logout`

`GET /auth/me` returns identity, `system_role`, `must_change_password`, and the
current user's workspace memberships. It never returns password, password hash,
session token, bearer token, or token hash.

### Superadmin user API

- `GET /admin/users?q=&status=&limit=&offset=`
- `GET /admin/users/{user_id}`
- `POST /admin/users`
- `PATCH /admin/users/{user_id}`
- `POST /admin/users/{user_id}/suspend`
- `POST /admin/users/{user_id}/reactivate`
- `POST /admin/users/{user_id}/reset-password`

Create accepts:

```json
{
  "email": "viewer@example.com",
  "display_name": "Viewer User",
  "system_role": "user",
  "initial_membership": {
    "workspace_id": "00000000-0000-0000-0000-000000000001",
    "role": "viewer"
  }
}
```

For a superadmin, `system_role` is `superadmin` and `initial_membership` must be
absent. Create and reset responses use the one-time shape:

```json
{
  "user": {},
  "temporary_password": "plaintext-returned-once"
}
```

The list response is paginated and contains summaries. The detail response adds
all memberships. Neither response exposes credential or session material.

### Workspace member API

- `GET /workspaces/{workspace_id}/members`
- `POST /workspaces/{workspace_id}/members`
- `PATCH /workspaces/{workspace_id}/members/{user_id}`
- `DELETE /workspaces/{workspace_id}/members/{user_id}`

Add accepts exact email plus role. List responses embed the safe user summary so
the frontend shows email and display name rather than raw UUIDs. Update accepts
only a workspace role. Delete removes only the membership.

The existing UUID-based membership routes can remain as compatibility aliases
during this change, but the frontend and new tests use `/members`. Compatibility
aliases must call the same service methods and authorization checks.

### Stable error codes

The API uses stable codes for at least:

- `setup_required`;
- `invalid_credentials`;
- `email_already_exists`;
- `password_change_required`;
- `last_active_superadmin`;
- `last_workspace_admin`;
- `user_not_found_or_not_addable`;
- `membership_already_exists`;
- `workspace_access_required`;
- `workspace_admin_required`;
- `superadmin_required`.

## Frontend Design

### Authentication boundary

The SPA adds focused login and mandatory-password-change views. It no longer
loads workspaces, chat history, settings, or other protected data until the
current session is resolved and `must_change_password` is false.

The API client sends cookies with `credentials: "include"` and attaches the
in-memory CSRF token to unsafe requests. It never stores a human session or CSRF
token in local storage. `VITE_ADAPTIVE_RAG_AUTH_TOKEN` is removed from the human
browser flow; dependency-injected bearer auth remains available to tests and
technical clients.

### Navigation by role

- Superadmins see global Users and workspace Members management.
- Workspace admins see Members for the selected workspace but no global Users
  directory or global identity actions.
- Contributors and viewers do not see Users/Members navigation or controls.

The selected workspace's live `access_role` drives workspace navigation. The
frontend does not infer one global workspace role from another membership.

### Global users view

The superadmin view follows the proven BeFlow interaction structure:

- search by email or display name;
- active/suspended filter;
- paginated responsive table on desktop and cards on mobile;
- create-user action;
- per-user detail and membership list;
- edit, reset password, suspend, and reactivate actions;
- explicit confirmation for suspension and reset.

Actions that would violate last-superadmin or last-workspace-admin rules are
disabled when the UI has enough server-authoritative data, and the API error is
still handled if concurrent state changes.

### Workspace members view

The workspace-admin view shows only the selected workspace's members. It allows:

- exact-email member addition;
- `viewer`, `contributor`, or `admin` assignment;
- role change;
- membership removal;
- visible last-admin protection.

It contains no global user search, global status, password, email-edit, or
superadmin controls.

### One-time temporary password component

A reusable `OneTimePasswordDialog` opens after user creation or password reset.
It displays:

- the target email;
- a masked/revealable temporary password;
- a one-time visibility warning;
- a selectable password field;
- `Copy password`;
- an accessible copied/error status.

If Clipboard API access fails, the password remains selectable for manual copy.
Closing requires the administrator to acknowledge that the password was saved.
Close clears the plaintext from React state. The value is never written to local
storage, logs, error reporting, analytics, URLs, or query caches.

Loading, validation, and durable errors remain inline. Copy success is transient
and announced accessibly.

## Migration and Compatibility

The migration sequence is:

1. Preflight all existing `users.login` values by trimming, lowercasing, and
   validating email syntax.
2. Abort with an actionable error if normalization creates a duplicate or any
   value is invalid.
3. Rename `users.login` to `users.email` and preserve the unique constraint.
4. Create password-credential, human-session, and login-rate-limit persistence.
5. Preserve existing `user_access_tokens` and bearer authentication.
6. Remove unrestricted empty-table bootstrap behavior and add the explicit
   setup endpoint.

Existing users do not receive generated passwords during migration because a
plaintext password cannot be safely recovered or delivered. An existing
superadmin authenticates with the existing technical bearer token and invokes
reset-password for each human account that needs browser login. This transition
is documented in the operator runbook.

## Transactions and Concurrency

The service layer owns transaction boundaries for:

- user plus password credential plus initial membership creation;
- last-active-superadmin checks and mutations;
- last-workspace-admin checks and mutations;
- password reset plus session revocation;
- suspension plus session revocation;
- email change plus session revocation.

Repositories flush but do not commit. Last-administrator operations lock the
relevant user or membership set before counting and mutating. Tests must prove
that two concurrent requests cannot both pass a stale count and remove the final
protected administrator.

## Security and Audit Requirements

- Use Python's cryptographic `secrets` module for temporary passwords, session
  tokens, and CSRF tokens.
- Store password hashes with Argon2id, never SHA-256 or reversible encryption.
- Store only hashes of sessions, CSRF tokens, and bearer tokens.
- Compare bootstrap and CSRF secrets in constant time.
- Never log request bodies for login, change-password, reset-password, or setup.
- Emit structured security events with actor ID, target user ID, workspace ID
  when applicable, action, result, and timestamp; never include secret values.
- Deny inactive users and revoked/expired sessions before workspace
  authorization.
- Apply authorization on every server route; hidden UI is not sufficient.
- Return generic login and exact-email-add errors to limit user enumeration.

References:

- [OWASP Password Storage Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html)
- [OWASP Secrets Management Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html)
- [NIST SP 800-63B password authenticators](https://pages.nist.gov/800-63-4/sp800-63b/authenticators/)
- [Python `secrets`](https://docs.python.org/3/library/secrets.html)

## Verification Strategy

### Backend

- Model constraints for normalized unique email, one password credential per
  user, session hashes, and one role per user/workspace.
- Password hashing/verification, mandatory change, reset, and no plaintext
  persistence.
- Session login, logout, rotation, idle expiry, absolute expiry, revocation, and
  inactive-user rejection.
- Cookie and CSRF enforcement, including Origin checks and bearer-token
  exemption.
- Login throttling and non-enumerating responses.
- Full endpoint permission matrix for viewer, contributor, admin, and
  superadmin.
- A discriminating multi-workspace case where one user is viewer in workspace 1
  and admin in workspace 2.
- Exact-email member addition without a global directory leak.
- IDOR attempts across users and workspaces.
- Suspension/reactivation and password-reset lifecycle.
- Last-superadmin and last-workspace-admin checks, including concurrent
  transactions on PostgreSQL.
- Alembic upgrade from the previous head, data preservation, invalid-email
  preflight failure, downgrade shape if repository policy requires it, and a
  single migration head.

### Frontend

- Login success/failure and no credential persistence.
- Mandatory password-change routing and API blocking.
- Navigation visibility for each effective role.
- Global directory visible only to superadmin.
- Workspace admin sees only selected-workspace members.
- Same user renders different actions after switching between viewer and admin
  workspaces.
- Create, edit, suspend/reactivate, reset, add member, change role, and remove
  member flows.
- One-time password reveal, copy success, clipboard failure fallback,
  acknowledgement, and plaintext clearing on close.
- Responsive table/card behavior and accessible dialog/status semantics.

### End to end

The acceptance flow is:

1. Start with zero users and complete bootstrap using the configured setup
   secret.
2. Copy the first superadmin's temporary password and complete mandatory change.
3. Create two workspaces.
4. Create a normal user as viewer in workspace 1 and copy the temporary
   password.
5. Add the same user as admin in workspace 2.
6. Log in as that user and change the temporary password.
7. Verify RAG access but no member administration in workspace 1.
8. Verify inherited contributor capabilities and member administration in
   workspace 2.
9. Verify no access to a third workspace.
10. Suspend the user and verify immediate session rejection.
11. Reactivate and reset the password; verify old credentials/sessions fail and
    the new temporary password requires another change.
12. Exercise last-admin and last-superadmin protections.

## Success Criteria

The feature is complete when:

- a human can authenticate without an API key;
- no plaintext password, session token, CSRF token, or bearer token is persisted
  or logged;
- the same identity can hold different effective roles in different workspaces;
- workspace admins manage only their workspace's memberships;
- superadmins manage all identities and workspaces without bypassing last-admin
  invariants;
- temporary password creation/reset is copyable once and forces a password
  change;
- suspended users lose active access immediately and can be safely reactivated;
- backend, frontend, migration, concurrency, and end-to-end tests pass.
