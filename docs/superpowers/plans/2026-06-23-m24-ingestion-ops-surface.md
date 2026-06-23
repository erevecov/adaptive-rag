# M24 Ingestion Ops Surface Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the public ingestion operations surface that lets a local user enqueue, run, inspect and retry source ingestion jobs after M23 authoring.

**Architecture:** Add a shared `adaptive_rag.ingestion_ops` module over `JobRepository`, `SourceRepository` and `IngestionPipeline`; use thin API, CLI and frontend adapters. Keep M24 limited to document ingestion/job state and leave chunking, embeddings, indexing and onboarding for later milestones.

**Tech Stack:** FastAPI, Pydantic, Typer, SQLAlchemy repositories, React/TypeScript/Vite, Vitest, pytest, OpenSpec.

---

## File Structure

- `src/adaptive_rag/db/repositories/jobs.py`: add deterministic list and manual requeue.
- `src/adaptive_rag/ingestion/pipeline.py`: return observable blocked results from `run_next`.
- `src/adaptive_rag/ingestion_ops.py`: shared enqueue/list/show/retry/run-next operations and JSON payload helpers.
- `src/adaptive_rag/api/schemas/ingestion_ops.py`: request/response schemas for jobs and run reports.
- `src/adaptive_rag/api/routes/ingestion_ops.py`: project-scoped ingestion job endpoints.
- `src/adaptive_rag/api/app.py`: register ingestion ops router.
- `src/adaptive_rag/cli/jobs.py`: add enqueue/list/show/retry and reuse shared run-next reporting.
- `frontend/src/lib/apiClient.ts`: add ingestion job types and client methods.
- `frontend/src/App.tsx`: add compact ingestion controls in Authoring view.
- `frontend/src/App.css`: style job controls and status rows.
- Tests under `tests/unit/db/repositories/`, `tests/unit/ingestion/`,
  `tests/integration/api/`, `tests/integration/cli/`, and `frontend/src/`.

### Task 1: Backend Repository And Ops Contract

- [ ] Write failing tests for `JobRepository.list()` and `requeue()`.
- [ ] Implement the minimal repository methods.
- [ ] Write failing tests for `adaptive_rag.ingestion_ops` enqueue/list/show/retry.
- [ ] Implement shared ops and payload helpers.

### Task 2: Observable Pipeline Runs

- [ ] Write failing tests proving blocked jobs return an observable blocked result.
- [ ] Update `IngestionPipeline.run_next()` and CLI run-worker reporting.
- [ ] Confirm existing ingestion success/idempotency tests still pass.

### Task 3: API Surface

- [ ] Write failing API tests for enqueue/list/show/retry/run-next.
- [ ] Implement schemas/routes and register the router.
- [ ] Confirm API tests pass.

### Task 4: CLI Surface

- [ ] Write failing CLI tests for jobs enqueue/list/show/retry and blocked worker output.
- [ ] Implement CLI commands using `ingestion_ops`.
- [ ] Confirm CLI tests pass.

### Task 5: Frontend Surface

- [ ] Write failing `apiClient` tests for ingestion job methods.
- [ ] Implement frontend client types/methods.
- [ ] Write failing App test for enqueue/run/refresh/retry in Authoring.
- [ ] Implement compact UI controls and states.

### Task 6: Quality Gate And Archive

- [ ] Run backend and frontend validation.
- [ ] Validate OpenSpec active and specs.
- [ ] Archive M24.
- [ ] Update progress/roadmap to recommend M25 first-run onboarding.
