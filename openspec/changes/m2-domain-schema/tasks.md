# M2 Domain Schema Tasks

## 1. Planning and setup

- [ ] 1.1 Confirm this OpenSpec change is approved for implementation.
- [ ] 1.2 Create an implementation branch from current `origin/main`.
- [ ] 1.3 Run `uv sync --extra dev` and `uv run pytest` to confirm baseline.

## 2. SQLAlchemy models

- [ ] 2.1 Add failing tests for project defaults and embedding mode constraints.
- [ ] 2.2 Add SQLAlchemy models for `projects`, `sources`, `documents` and `document_versions`.
- [ ] 2.3 Add failing tests for chunk citation offsets and dense embedding dimensions.
- [ ] 2.4 Add SQLAlchemy models for `chunks` and `chunk_sparse_embeddings`.

## 3. Alembic migration

- [ ] 3.1 Add a migration that enables `vector` extension when needed.
- [ ] 3.2 Add tables, foreign keys, uniqueness constraints and check constraints.
- [ ] 3.3 Add indexes for project isolation and metadata filtering.
- [ ] 3.4 Keep dense retrieval exact; do not add HNSW in this change.

## 4. Integration validation

- [ ] 4.1 Add Postgres/pgvector integration tests for migration apply.
- [ ] 4.2 Verify `chunks.embedding vector(1024)` with a real Postgres container.
- [ ] 4.3 Verify project/source/document filters have indexed columns.

## 5. Quality gate and handoff

- [ ] 5.1 Run `uv run pytest`.
- [ ] 5.2 Run `uv run ruff check .`.
- [ ] 5.3 Run `uv run mypy src`.
- [ ] 5.4 Update `docs/progress-log/` with a new completion entry.
- [ ] 5.5 Open a PR and do not start repository-layer work until this schema PR is merged.

