# Propuesta M44 — CI + compose all-in-one + gate reconcile

## Why

Pre-v1 needs automated CI and a documented demo stack including frontend.
Quality-gate deferred defaults still list `auth_multi_user` after M37/M43.

## What Changes

- GitHub Actions: backend ruff/mypy/pytest, frontend test/typecheck/lint/build,
  openspec strict (no live Qwen).
- Compose frontend service + nginx static build; document alembic migrations.
- Remove `auth_multi_user` from deferred_defaults.
- No v1.0 tag/release from this change.
