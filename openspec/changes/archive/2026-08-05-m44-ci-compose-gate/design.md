# Diseno M44

CI runs three jobs on PR/main. Compose adds `frontend` built from
`frontend/Dockerfile` (pnpm build → nginx). Migrations remain
`uv run alembic upgrade head` against compose postgres.
