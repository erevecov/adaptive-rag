# Adaptive RAG Roadmap

## Current status

- M1 Foundation: complete.
- M2 Domain and persistence: planned.

## M1 Foundation

Status: complete.

Delivered:

- Python package scaffold.
- Settings and logging.
- SQLAlchemy base, DB session helpers and Alembic foundation.
- FastAPI app factory and `/health`.
- Typer CLI shell with `version` and `health`.
- Final quality gate passed on 2026-06-17.

## M2 Domain and persistence

Status: next.

Recommended sequence:

1. `m2-domain-schema`: SQLAlchemy models and Alembic migration for project/document/chunk schema.
2. `m2-repositories`: repository layer with project isolation and metadata filters.
3. `m2-job-queue`: jobs, job events, retries, blocked/dead-letter states and worker leasing.
4. `m2-url-fetch-policy`: SSRF, DNS rebinding, redirects, content type and response size protection.
5. `m2-quality-gate`: milestone-level validation and OpenSpec archive/sync.

Recommended next task: implement `m2-domain-schema` first, because every repository, ingestion and retrieval path depends on stable table names, keys and citation anchors.

## Merge conflict policy

- Only one active PR should touch Alembic migrations and SQLAlchemy models at a time.
- Start repository or worker branches only after the schema PR merges.
- Keep roadmap edits in planning or milestone-close PRs.
- Record daily progress in new files under `docs/progress-log/` instead of editing old entries.

