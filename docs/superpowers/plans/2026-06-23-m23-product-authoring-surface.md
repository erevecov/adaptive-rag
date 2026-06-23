# M23 Product Authoring Surface Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the public project/source authoring surface that lets a local user create a project and add Markdown, TXT or URL sources without direct SQL or private fixtures.

**Architecture:** Add thin API, CLI and frontend adapters over the existing SQLAlchemy repositories. Keep ingestion execution and job-state UI out of M23; M24 owns `ingest_source` job creation, monitoring and retry flows. Do not change retrieval defaults, graph defaults, provider runtime or auth.

**Tech Stack:** FastAPI, Pydantic, Typer, SQLAlchemy repositories, React/TypeScript/Vite, Vitest, pytest, OpenSpec.

---

## File Structure

- `src/adaptive_rag/api/schemas/authoring.py`: request/response schemas for projects and sources.
- `src/adaptive_rag/api/routes/authoring.py`: `POST/GET /projects`, `GET /projects/{project_id}`, `POST/GET /projects/{project_id}/sources`, and `GET /projects/{project_id}/sources/{source_id}`.
- `src/adaptive_rag/api/app.py`: register the authoring router.
- `src/adaptive_rag/cli/projects.py`: `adaptive-rag projects create|list|show`.
- `src/adaptive_rag/cli/sources.py`: `adaptive-rag sources create|list|show`.
- `src/adaptive_rag/cli/app.py`: register new CLI groups.
- `src/adaptive_rag/db/repositories/projects.py`: add deterministic `list()` if needed.
- `src/adaptive_rag/db/repositories/sources.py`: reuse existing `list()`, `get()` and `get_by_identity()`.
- `frontend/src/lib/apiClient.ts`: add project/source types and client methods.
- `frontend/src/App.tsx`: add compact setup/authoring controls without replacing chat.
- Tests under `tests/integration/api/`, `tests/integration/cli/`, `tests/unit/db/repositories/`, and `frontend/src/lib/`.

### Task 1: Repository And API Contract

**Files:**
- Modify: `src/adaptive_rag/db/repositories/projects.py`
- Create: `src/adaptive_rag/api/schemas/authoring.py`
- Create: `src/adaptive_rag/api/routes/authoring.py`
- Modify: `src/adaptive_rag/api/app.py`
- Test: `tests/unit/db/repositories/test_repositories.py`
- Test: `tests/integration/api/test_authoring.py`

- [ ] **Step 1: Write failing repository tests**

Add tests that prove `ProjectRepository.list()` returns projects ordered by `created_at`, then `name`, then `id`, and that project creation still flushes without commit.

Run: `uv run pytest tests/unit/db/repositories/test_repositories.py -q`
Expected: FAIL because `ProjectRepository.list()` does not exist yet.

- [ ] **Step 2: Implement `ProjectRepository.list()`**

Add a method that uses the caller-owned `Session`, returns `list[Project]`, and does not commit.

Run: `uv run pytest tests/unit/db/repositories/test_repositories.py -q`
Expected: PASS.

- [ ] **Step 3: Write failing API tests**

Cover:
- `POST /projects` creates a dense project by default and returns stable JSON.
- `GET /projects` lists created projects.
- `GET /projects/{project_id}` returns 404 for missing projects.
- `POST /projects/{project_id}/sources` creates `markdown`, `text`, `txt` and `url` sources.
- text-like sources require `extra_metadata.content`.
- duplicate `(project_id, source_type, external_id)` returns 409, not 500.
- source list/get never crosses project boundaries.

Run: `uv run pytest tests/integration/api/test_authoring.py -q`
Expected: FAIL because routes do not exist yet.

- [ ] **Step 4: Implement schemas and routes**

Expose only public fields:
- Project response: `id`, `name`, `embedding_mode`, `retrieval_contextualization_enabled`, `budget_config_json`, `created_at`, `updated_at`.
- Source response: `id`, `project_id`, `source_type`, `external_id`, `tags`, `extra_metadata`, `created_at`, `updated_at`.

Reject public project create modes other than `dense` in M23. Keep `dense_sparse` reserved for a future evidence-backed OpenSpec change.

Run: `uv run pytest tests/integration/api/test_authoring.py tests/unit/db/repositories/test_repositories.py -q`
Expected: PASS.

### Task 2: CLI Authoring

**Files:**
- Create: `src/adaptive_rag/cli/projects.py`
- Create: `src/adaptive_rag/cli/sources.py`
- Modify: `src/adaptive_rag/cli/app.py`
- Test: `tests/integration/cli/test_authoring_cli.py`

- [ ] **Step 1: Write failing CLI tests**

Cover JSON output for:
- `adaptive-rag projects create --name demo`
- `adaptive-rag projects list`
- `adaptive-rag projects show --project-id <uuid>`
- `adaptive-rag sources create --project-id <uuid> --source-type markdown --external-id notes.md --content "# Notes" --tag docs`
- `adaptive-rag sources create --project-id <uuid> --source-type url --external-id https://example.com/doc`
- `adaptive-rag sources list --project-id <uuid>`
- missing project/source errors return non-zero exit and stable stderr.

Run: `uv run pytest tests/integration/cli/test_authoring_cli.py -q`
Expected: FAIL because CLI groups do not exist yet.

- [ ] **Step 2: Implement CLI groups**

Use `session_scope()` and repositories directly. Emit compact JSON to stdout and user-facing errors to stderr. Do not start ingestion jobs from these commands.

Run: `uv run pytest tests/integration/cli/test_authoring_cli.py -q`
Expected: PASS.

### Task 3: Frontend Client And UI

**Files:**
- Modify: `frontend/src/lib/apiClient.ts`
- Modify: `frontend/src/lib/apiClient.test.ts`
- Modify: `frontend/src/App.tsx`
- Test: frontend tests around client and app behavior.

- [ ] **Step 1: Add failing client tests**

Cover project/source create/list/show URLs, request bodies, query params and error preservation.

Run: `pnpm --dir frontend test -- apiClient`
Expected: FAIL because client methods do not exist yet.

- [ ] **Step 2: Implement client types and methods**

Add typed methods:
- `createProject(body)`
- `listProjects()`
- `getProject(projectId)`
- `createSource(projectId, body)`
- `listSources(projectId, params)`
- `getSource(projectId, sourceId)`

Run: `pnpm --dir frontend test -- apiClient`
Expected: PASS.

- [ ] **Step 3: Add authoring UI**

Add compact controls for creating/selecting a project and adding/listing sources. Keep chat and observability as working surfaces; do not create a marketing page or nested cards.

Run: `pnpm --dir frontend test`
Expected: PASS.

### Task 4: M23 Quality Gate And Archive

**Files:**
- Modify: `docs/progress.md`
- Modify: `docs/roadmap.md`
- Archive: `openspec/changes/m23-product-authoring-surface/`

- [ ] **Step 1: Run backend and frontend gates**

Run:
- `uv run pytest`
- `uv run ruff check .`
- `uv run mypy src`
- `pnpm --dir frontend test`
- `pnpm --dir frontend run typecheck`
- `pnpm --dir frontend run lint`
- `pnpm --dir frontend run build`

Expected: all pass.

- [ ] **Step 2: Run OpenSpec gates**

Run:
- `npx --yes @fission-ai/openspec validate m23-product-authoring-surface --strict`
- `npx --yes @fission-ai/openspec validate --specs --strict`
- `npx --yes @fission-ai/openspec list`
- `git diff --check`

Expected: active M23 validates before archive; no active changes after archive.

- [ ] **Step 3: Archive M23 after implementation**

Use `npx --yes @fission-ai/openspec archive m23-product-authoring-surface --yes`, then update progress and roadmap to recommend `m24-ingestion-ops-surface`.
