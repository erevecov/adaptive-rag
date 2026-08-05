# Propuesta M43 — authoring lifecycle + RBAC closeout

## Why

Projects/sources are create/list only. Memberships cannot be deleted; users
cannot be deactivated nor tokens revoked via public API. Pre-v1 needs lifecycle
closeout with role matrix coverage.

## What Changes

- PATCH/DELETE (soft) projects and sources; source delete cascades index rows.
- DELETE membership; deactivate user; revoke access token.
- Role matrix tests (viewer denied, admin/contributor as appropriate).
- Minimal confirmation pattern for destructive UI actions (API-first).

## Fuera de alcance

- Full admin UI redesign, multi-tenant SaaS, OAuth.
