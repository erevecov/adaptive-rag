# PostgreSQL Job Platform Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the ingestion-specific long-transaction worker with a general PostgreSQL job platform that supports workspace and system jobs, fair global workers, fenced attempts, retries, cancellation, durable cron schedules, operational APIs/CLI, and a web console.

**Architecture:** `jobs` remains the canonical logical record while `job_attempts` owns leases and fencing. Short PostgreSQL transactions admit and transition work; handlers run outside those transactions through a code registry. Scheduler, worker, reaper, API, CLI, and React console share the same services and retain the existing ingestion and system-task surfaces as compatibility adapters.

**Tech Stack:** Python 3.12+, SQLAlchemy 2, Psycopg 3, PostgreSQL 16, Alembic, Pydantic 2, FastAPI, Typer, croniter 6.2, pytest/Testcontainers, React 19, TypeScript, Tailwind utilities, Vitest.

## Global Constraints

- PostgreSQL is the only durable queue and scheduling dependency.
- Execution is at-least-once; never describe external effects as exactly-once.
- A job is either `scope="workspace"` with a non-null `workspace_id`, or `scope="system"` with a null `workspace_id`.
- Job handlers are code-registered and versioned; payloads cannot select shell commands, imports, modules, callables, or executors.
- Claim, heartbeat, progress, and finalization transactions are short; handler execution never shares the claim transaction.
- Every attempt UUID is a fencing token; stale attempts must update zero canonical rows.
- Existing job UUIDs, provider-usage references, ingestion API/CLI/UI behavior, and contributor authorization remain compatible.
- Generic workspace mutations require workspace admin; system-scope and global queue/worker operations require superadmin.
- Hard caps: payload 256 KiB, result 64 KiB, progress 8 KiB, event metadata 16 KiB, safe error 4 KiB, page size 200, absolute priority 1,000, retries 25, lease 3,600 seconds, catch-up 100, persisted progress 1/second/attempt.
- Identifiers are bounded: handler and queue slugs match `[a-z][a-z0-9_-]{0,99}`; idempotency and concurrency keys are 1-255 UTF-8 bytes; worker IDs are UUIDs and process-identity labels are 1-128 bytes; schedule names are 1-200 bytes.
- Runtime defaults are explicit: leases 300 seconds with allowed range 15-3,600; attempt heartbeat `min(30, lease/3)` seconds; worker-presence heartbeat 10 seconds and stale threshold 30; idle poll 5; reaper tick 15; graceful drain 30; local concurrency 4.
- Cron is five-field with IANA time zones; default misfire policy is `run_once`.
- Use TDD for every production behavior: write the test, run the expected failure, implement minimally, and rerun focused plus affected tests.
- No unrelated refactors; every changed line must serve the approved design in `docs/superpowers/specs/2026-08-10-postgresql-job-platform-design.md`.

## File Map

- `src/adaptive_rag/db/models/job.py` and `job_event.py`: canonical job and event compatibility fields.
- `src/adaptive_rag/db/models/job_attempt.py`: attempt history, lease, fencing, progress, and structured failure.
- `src/adaptive_rag/db/models/job_queue.py`: queue capacity and per-scope dispatch cursor.
- `src/adaptive_rag/db/models/job_schedule.py`: durable cron definitions.
- `src/adaptive_rag/db/models/job_worker.py`: worker presence and supported capabilities.
- `src/adaptive_rag/db/repositories/jobs.py`: logical job enqueue, lookup, filtering, idempotency, and compatibility methods.
- `src/adaptive_rag/db/repositories/job_runtime.py`: claims, attempts, fencing transitions, reaping, progress, and worker presence.
- `src/adaptive_rag/db/repositories/job_schedules.py`: schedule locking and occurrence persistence.
- `src/adaptive_rag/jobs/registry.py`: handler definitions and payload/result validation.
- `src/adaptive_rag/jobs/service.py`: application operations for enqueue, cancel, retry, unblock, list, and detail.
- `src/adaptive_rag/jobs/dispatcher.py`: fair capacity admission and claimed-job snapshots.
- `src/adaptive_rag/jobs/worker.py`: async orchestration, sync/async invocation, heartbeat, polling, and drain.
- `src/adaptive_rag/jobs/scheduler.py`: cron occurrence calculation and replicated scheduler loop.
- `src/adaptive_rag/jobs/handlers.py`: ingestion, indexing, and provider-pricing registrations.
- `src/adaptive_rag/api/schemas/jobs.py` and `api/routes/jobs.py`: workspace and superadmin control plane.
- `src/adaptive_rag/cli/jobs.py`: general worker, scheduler, job, queue, worker, and schedule commands plus aliases.
- `frontend/src/features/jobs/`: Background Jobs console and pure UI helpers.
- `tests/integration/jobs/`: real-PostgreSQL concurrency, scheduler, worker-failure, and acceptance tests.

---

### Task 1: Additive schema and SQLAlchemy models

**Files:**
- Create: `alembic/versions/p5q6r7s8t9u0_job_platform.py`
- Create: `src/adaptive_rag/db/models/job_attempt.py`
- Create: `src/adaptive_rag/db/models/job_queue.py`
- Create: `src/adaptive_rag/db/models/job_schedule.py`
- Create: `src/adaptive_rag/db/models/job_worker.py`
- Modify: `src/adaptive_rag/db/models/job.py`
- Modify: `src/adaptive_rag/db/models/job_event.py`
- Modify: `src/adaptive_rag/db/models/__init__.py`
- Test: `tests/unit/db/models/test_job_platform_models.py`
- Test: `tests/integration/db/test_schema_pgvector.py`

**Interfaces:**
- Consumes: existing `Job`, `JobEvent`, `Workspace`, `JSONWithJSONB`, Alembic head `n4o5p6q7r8s9`.
- Produces: `JobAttempt`, `JobQueue`, `JobQueueWorkspaceState`, `JobSchedule`, `JobWorker`; expanded `Job` and `JobEvent` mappings used by every later task.

- [ ] **Step 1: Write model tests that describe the new state and scope checks**

```python
def test_job_platform_models_expose_fenced_runtime_state() -> None:
    assert set(JOB_STATUS_VALUES) == {
        "queued", "running", "succeeded", "blocked", "dead_letter", "cancelled"
    }
    job = Job(
        scope="system",
        workspace_id=None,
        queue_name="system",
        job_type="provider_model_pricing_sync",
        handler_version=1,
        payload_json={},
    )
    assert job.scope == "system"
    assert job.attempt_count == 0
    assert job.retry_count == 0


def test_attempt_uuid_is_the_fencing_token() -> None:
    attempt_id = uuid4()
    attempt = JobAttempt(id=attempt_id, job_id=uuid4(), scope="system", attempt_number=1,
                         worker_id=uuid4(), lease_expires_at=utc_now())
    assert attempt.id == attempt_id
    assert attempt.status == "running"
```

- [ ] **Step 2: Run the model tests and verify RED**

Run: `uv run pytest tests/unit/db/models/test_job_platform_models.py -q`

Expected: collection fails because `JobAttempt`, `JobQueue`, `JobSchedule`, and `JobWorker` are not defined.

- [ ] **Step 3: Add the SQLAlchemy models and compatibility fields**

Implement the constants and mappings with these canonical shapes:

```python
JOB_SCOPE_VALUES = ("workspace", "system")
JOB_STATUS_VALUES = (
    "queued", "running", "succeeded", "blocked", "dead_letter", "cancelled"
)
JOB_ATTEMPT_STATUS_VALUES = (
    "running", "succeeded", "retryable_failed", "blocked",
    "dead_letter", "expired", "cancelled", "fenced",
)
JOB_MISFIRE_POLICY_VALUES = ("skip", "run_once", "catch_up")
```

Keep `attempts`, `max_attempts`, `locked_by`, `locked_until`, and `last_error` mapped during compatibility. Add the approved canonical fields, including `idempotency_fingerprint`, scope check constraints, bounds, relationships, and indexes. Attempt `worker_id` is a UUID without a foreign key so immutable attempt audit survives pruning operational presence rows; compatibility `locked_by` stores its string form. Use UUID defaults from `uuid4` and `JSONWithJSONB` for SQLite/PostgreSQL portability.

- [ ] **Step 4: Run the model tests and verify GREEN**

Run: `uv run pytest tests/unit/db/models/test_job_platform_models.py tests/unit/db/models/test_job_queue.py -q`

Expected: PASS.

- [ ] **Step 5: Add a migration/backfill integration test before the migration**

```python
def test_job_platform_migration_backfills_existing_jobs(pg_url: str, pg_engine: Engine) -> None:
    run_alembic_upgrade(pg_url, target="n4o5p6q7r8s9")
    workspace_id, job_id = insert_legacy_job(pg_engine, attempts=2, max_attempts=3)
    run_alembic_upgrade(pg_url)
    with pg_engine.connect() as connection:
        row = connection.execute(
            text("SELECT scope, queue_name, handler_version, attempt_count, retry_count "
                 "FROM jobs WHERE id=:id"), {"id": job_id}
        ).mappings().one()
    assert row == {
        "scope": "workspace", "queue_name": "ingestion", "handler_version": 1,
        "attempt_count": 2, "retry_count": 2,
    }
```

- [ ] **Step 6: Run the migration test and verify RED**

Run: `uv run pytest tests/integration/db/test_schema_pgvector.py::test_job_platform_migration_backfills_existing_jobs -q`

Expected: FAIL because revision `p5q6r7s8t9u0` and the new columns do not exist.

- [ ] **Step 7: Implement the additive Alembic migration**

Create all new tables, seed `default`, `ingestion`, and `system` queue rows with the 300-second default lease, backfill existing jobs, replace status/event check constraints, add partial idempotency indexes for workspace and system scopes, add unique `(schedule_id, scheduled_for)`, and install an `AFTER INSERT` trigger on `jobs` that calls `pg_notify('adaptive_rag_jobs', NEW.queue_name)` at transaction commit. Backfill legacy `retry_count` as zero for blocked jobs and `min(attempts, max_attempts)` otherwise. Validate backfill counts, then make required columns non-null. The downgrade removes the trigger/function before dropping new tables/indexes/columns and restores legacy constraints; document that data written by the new runtime is not semantically recoverable after downgrade.

- [ ] **Step 8: Verify migrations and all affected models**

Run: `uv run alembic heads && uv run pytest tests/integration/db/test_schema_pgvector.py tests/unit/db/models/test_job_platform_models.py tests/unit/db/models/test_job_queue.py -q`

Expected: one head `p5q6r7s8t9u0`; PASS.

- [ ] **Step 9: Commit the schema slice**

```bash
git add alembic/versions/p5q6r7s8t9u0_job_platform.py src/adaptive_rag/db/models tests/unit/db/models/test_job_platform_models.py tests/integration/db/test_schema_pgvector.py
git commit -m "feat(jobs): add job platform schema"
```

---

### Task 2: Define handler registry, limits, errors, and typed context

**Files:**
- Create: `src/adaptive_rag/jobs/__init__.py`
- Create: `src/adaptive_rag/jobs/errors.py`
- Create: `src/adaptive_rag/jobs/registry.py`
- Create: `src/adaptive_rag/jobs/types.py`
- Test: `tests/unit/jobs/test_registry.py`
- Test: `tests/unit/jobs/test_job_types.py`

**Interfaces:**
- Consumes: Pydantic `BaseModel`, `WORKSPACE_ROLE_VALUES`, global hard caps from the approved spec.
- Produces: `HandlerKey`, `JobRegistry`, `JobHandlerDefinition`, `RetryPolicy`, `ConcurrencyPolicy`, `JobContext`, `RetryableJobError`, `BlockedJobError`, `PermanentJobError`, `JobCancelled`, `JobSecretMaterialError`.

- [ ] **Step 1: Write failing registry and payload-limit tests**

```python
class EchoPayload(BaseModel):
    message: str


def test_registry_validates_payload_and_manual_role() -> None:
    registry = JobRegistry()
    registry.register(JobHandlerDefinition(
        name="echo", version=1, payload_model=EchoPayload,
        handler=lambda _context, payload: {"echo": payload.message},
        queue_name="default", allow_manual_enqueue=True,
        minimum_manual_role="admin",
    ))
    payload = registry.validate_payload("echo", 1, {"message": "hello"})
    assert payload == EchoPayload(message="hello")
    assert registry.get("echo", 1).minimum_manual_role == "admin"


def test_registry_rejects_unknown_handler_and_oversized_payload() -> None:
    registry = JobRegistry()
    with pytest.raises(UnknownJobHandlerError):
        registry.validate_payload("payload.module:callable", 1, {})
    with pytest.raises(JobPayloadTooLargeError):
        ensure_json_size({"data": "x" * (256 * 1024)}, limit_bytes=256 * 1024)


def test_registry_rejects_raw_secret_fields_before_model_validation() -> None:
    with pytest.raises(JobSecretMaterialError):
        registry.validate_payload("echo", 1, {"message": "hi", "api_key": "raw"})
```

- [ ] **Step 2: Run the registry tests and verify RED**

Run: `uv run pytest tests/unit/jobs/test_registry.py tests/unit/jobs/test_job_types.py -q`

Expected: collection fails because `adaptive_rag.jobs` does not exist.

- [ ] **Step 3: Implement minimal public types and registry**

Use these stable signatures:

```python
JobScope = Literal["workspace", "system"]
HandlerKey = tuple[str, int]
JobHandler = Callable[["JobContext", BaseModel], object | Awaitable[object]]
Redactor = Callable[[object], object]


@dataclass(frozen=True, slots=True)
class RetryPolicy:
    max_retries: int = 3
    base_delay_seconds: float = 1.0
    max_delay_seconds: float = 60.0


@dataclass(frozen=True, slots=True)
class ConcurrencyPolicy:
    handler_limit: int | None = None
    key_limit: int | None = None


@dataclass(frozen=True, slots=True)
class JobHandlerDefinition:
    name: str
    version: int
    payload_model: type[BaseModel]
    handler: JobHandler
    queue_name: str
    default_priority: int = 0
    retry_policy: RetryPolicy = field(default_factory=RetryPolicy)
    lease_seconds: int = 300
    concurrency: ConcurrencyPolicy = field(default_factory=ConcurrencyPolicy)
    concurrency_key: Callable[[BaseModel], str | None] | None = None
    allowed_scopes: frozenset[JobScope] = frozenset({"workspace"})
    allow_manual_enqueue: bool = False
    minimum_manual_role: str = "admin"
    redact_payload: Redactor = redact_secret_keys
    redact_result: Redactor = redact_secret_keys
    redact_error: Redactor = redact_error_message


class JobRegistry:
    def register(self, definition: JobHandlerDefinition) -> None: ...
    def get(self, name: str, version: int) -> JobHandlerDefinition: ...
    def validate_payload(self, name: str, version: int,
                         raw: Mapping[str, object]) -> BaseModel: ...
    def manual_definitions(self, *, minimum_role: str) -> tuple[JobHandlerDefinition, ...]: ...
```

Validate handler and queue names as bounded slugs, version as a positive integer, priority/lease/retry/concurrency values against Global Constraints, non-empty scopes, and `minimum_manual_role` against the workspace role hierarchy. Before Pydantic validation, recursively reject case-insensitive payload keys `password`, `secret`, `token`, `api_key`, `authorization`, `private_key`, and suffixes matching `_password`, `_secret`, or `_token`; handlers receive credential/resource IDs instead. Redact the same keys from results and event metadata before persistence. Reject Pydantic `SecretStr`/`SecretBytes` values rather than serializing masks as usable data. `JobContext` exposes immutable IDs plus `is_cancel_requested()`, `raise_if_cancelled()`, and `report_progress(progress: Mapping[str, object])`. Implement callbacks as injected protocols so tests do not need a database.

- [ ] **Step 4: Add failure-classification and full-jitter tests**

```python
@pytest.mark.parametrize("retry_count,upper", [(0, 1.0), (1, 2.0), (6, 60.0)])
def test_full_jitter_is_bounded(retry_count: int, upper: float) -> None:
    delay = retry_delay_seconds(RetryPolicy(max_retries=8), retry_count,
                                random_value=0.5)
    assert delay == upper * 0.5
```

- [ ] **Step 5: Implement errors, size/redaction helpers, and retry calculation**

`retry_delay_seconds(policy, retry_count, random_value)` must compute `random_value * min(max_delay, base_delay * 2**retry_count)` and reject random values outside `[0, 1]`. Truncate safe messages to 4 KiB after UTF-8 encoding.

- [ ] **Step 6: Verify strict typing and tests**

Run: `uv run pytest tests/unit/jobs/test_registry.py tests/unit/jobs/test_job_types.py -q && uv run mypy src/adaptive_rag/jobs`

Expected: PASS with no type errors.

- [ ] **Step 7: Commit the handler contract**

```bash
git add src/adaptive_rag/jobs tests/unit/jobs
git commit -m "feat(jobs): add typed handler registry"
```

---

### Task 3: Implement transactional enqueue, idempotency, listing, and redaction

**Files:**
- Create: `src/adaptive_rag/jobs/service.py`
- Modify: `src/adaptive_rag/db/repositories/jobs.py`
- Modify: `src/adaptive_rag/db/repositories/__init__.py`
- Test: `tests/unit/jobs/test_job_service.py`
- Test: `tests/integration/jobs/conftest.py`
- Test: `tests/integration/jobs/test_enqueue_pg.py`

**Interfaces:**
- Consumes: Task 1 models and Task 2 `JobRegistry`.
- Produces: `JobService.enqueue`, `JobService.list_jobs`, `JobService.get_detail`; `EnqueueJobRequest`, `EnqueueJobResult`, `JobPage`, `JobDetail`. Task 5 adds lifecycle mutations.

- [ ] **Step 1: Write the failing service-level enqueue test**

```python
def test_enqueue_validates_and_returns_existing_matching_open_job(session, registry) -> None:
    service = JobService(session=session, registry=registry)
    request = EnqueueJobRequest.workspace(
        workspace_id=WORKSPACE_ID, job_type="echo", payload={"message": "hi"},
        idempotency_key="message-1",
    )
    first = service.enqueue(request)
    second = service.enqueue(request)
    assert first.created is True
    assert second.created is False
    assert second.job.id == first.job.id
```

- [ ] **Step 2: Run the service test and verify RED**

Run: `uv run pytest tests/unit/jobs/test_job_service.py::test_enqueue_validates_and_returns_existing_matching_open_job -q`

Expected: import fails because `JobService` is not defined.

- [ ] **Step 3: Implement request/result types and enqueue through the caller session**

```python
@dataclass(frozen=True, slots=True)
class EnqueueJobResult:
    job: Job
    created: bool


class JobService:
    def enqueue(self, request: EnqueueJobRequest) -> EnqueueJobResult:
        definition = self._registry.get(request.job_type, request.handler_version)
        payload = definition.payload_model.model_validate(request.payload)
        return self._repository.enqueue_validated(request, payload.model_dump(mode="json"))
```

The repository flushes but never commits. It creates `created` and `queued` events. The migration-owned `AFTER INSERT` trigger performs `pg_notify`, whose delivery is transactional in PostgreSQL, so a rollback cannot wake a worker for invisible work. SQLite tests do not emulate notifications; worker polling is the portable fallback.

Enqueue rejects a queue absent from `job_queues` and upserts `(queue_name, scope_key)` in `job_queue_workspace_state` inside the same transaction. New application queues therefore require an explicit migration or superadmin queue-creation operation; handlers cannot create infrastructure implicitly from payload data.

- [ ] **Step 4: Add idempotency-conflict and system-scope tests**

```python
def test_same_key_with_different_payload_is_conflict(session, registry) -> None:
    service = JobService(session=session, registry=registry)
    service.enqueue(system_request(key="same", message="one"))
    with pytest.raises(JobIdempotencyConflictError):
        service.enqueue(system_request(key="same", message="two"))


def test_workspace_and_system_keys_do_not_collide(session, registry) -> None:
    workspace = JobService(session=session, registry=registry).enqueue(
        workspace_request(key="daily"))
    system = JobService(session=session, registry=registry).enqueue(
        system_request(key="daily"))
    assert workspace.job.id != system.job.id
```

- [ ] **Step 5: Implement cursor pagination and redacted detail snapshots**

Use opaque base64url cursors over `(created_at, id)` and always add UUID as the final order key. `list_jobs` accepts `scope`, workspace, status, queue, job type, schedule, created range, cursor, and `limit<=200`. `get_detail` returns bounded attempts/events and uses the handler redactor for payload/result fields.

- [ ] **Step 6: Write the real-PostgreSQL rollback/concurrency tests**

```python
def test_rolled_back_enqueue_is_never_visible(pg_session_factory, registry) -> None:
    with pg_session_factory() as session:
        result = JobService(session=session, registry=registry).enqueue(system_request())
        job_id = result.job.id
        session.rollback()
    with pg_session_factory() as session:
        assert session.get(Job, job_id) is None


def test_concurrent_idempotent_enqueue_creates_one_open_job(pg_session_factory, registry) -> None:
    ids = run_concurrently(8, lambda: enqueue_and_commit(pg_session_factory, registry,
                                                        key="shared"))
    assert len(set(ids)) == 1


def test_idempotency_race_does_not_rollback_business_write(pg_session_factory, registry) -> None:
    winner = race_enqueue_with_business_row(pg_session_factory, registry, key="shared")
    assert load_business_row(pg_session_factory, winner.business_id) is not None
```

- [ ] **Step 7: Implement race-safe savepoint recovery and canonical fingerprints**

Canonicalize JSON with sorted keys and compact separators, and hash scope, workspace ID, handler key, payload, queue, priority, requested `run_after` (including null), schedule occurrence, and concurrency key with SHA-256. Store the lowercase hex digest only when `idempotency_key` is present. Perform the insert/flush in `session.begin_nested()`; on the named open-key unique violation, roll back only the savepoint, load the conflicting row in the still-valid outer transaction, and return it only when the fingerprint matches. Re-raise unrelated integrity errors. Neither repository nor service commits or rolls back the caller's outer transaction.

- [ ] **Step 8: Run service and PostgreSQL enqueue tests**

Run: `uv run pytest tests/unit/jobs/test_job_service.py tests/integration/jobs/test_enqueue_pg.py -q`

Expected: PASS; the PostgreSQL count for the concurrent key is one.

- [ ] **Step 9: Commit enqueue and read operations**

```bash
git add src/adaptive_rag/jobs/service.py src/adaptive_rag/db/repositories tests/unit/jobs/test_job_service.py tests/integration/jobs
git commit -m "feat(jobs): add transactional enqueue service"
```

---

### Task 4: Add fair claims, capacity admission, and fencing

**Files:**
- Create: `src/adaptive_rag/db/repositories/job_runtime.py`
- Create: `src/adaptive_rag/jobs/dispatcher.py`
- Modify: `src/adaptive_rag/db/repositories/__init__.py`
- Test: `tests/unit/jobs/test_dispatcher.py`
- Test: `tests/integration/jobs/test_claims_pg.py`

**Interfaces:**
- Consumes: `JobQueue`, `JobQueueWorkspaceState`, `JobAttempt`, `JobRegistry`.
- Produces: `JobDispatcher.claim_next(...) -> ClaimedJob | None`, `JobRuntimeRepository.heartbeat`, and conditional fenced transitions used by the worker and reaper.

- [ ] **Step 1: Write the PostgreSQL duplicate-claim and visibility tests**

```python
def test_two_workers_create_one_attempt_for_one_job(pg_session_factory, registry) -> None:
    job_id = enqueue_ready_job(pg_session_factory, registry)
    claims = run_concurrently(
        2, lambda index: claim_and_commit(pg_session_factory, registry,
                                          worker_id=uuid4()))
    assert [claim.job_id for claim in claims if claim is not None] == [job_id]
    assert count_attempts(pg_session_factory, job_id) == 1


def test_claim_is_committed_before_handler_work(pg_session_factory, registry) -> None:
    claim = claim_and_commit(pg_session_factory, registry, worker_id=uuid4())
    with pg_session_factory() as observer:
        observed = observer.get(Job, claim.job_id)
        assert observed.status == "running"
        assert observed.current_attempt_id == claim.attempt_id
```

- [ ] **Step 2: Run claim tests and verify RED**

Run: `uv run pytest tests/integration/jobs/test_claims_pg.py::test_two_workers_create_one_attempt_for_one_job -q`

Expected: import fails because `JobDispatcher` is not defined.

- [ ] **Step 3: Implement the short claim transaction**

`claim_next` must:

```python
def claim_next(self, *, worker_id: UUID, supported_handlers: Collection[HandlerKey],
               queue_names: Collection[str], now: datetime) -> ClaimedJob | None:
    # caller opens and commits one short session around this call
```

Lock one queue row, calculate its running counts, select the oldest eligible `scope_key`, and lock that scope's highest-priority job with `FOR UPDATE SKIP LOCKED`. Before admission, acquire transaction-scoped PostgreSQL advisory locks for the handler key and optional concurrency key in sorted numeric order, then recheck those fleet-wide counts across every queue. Insert an attempt UUID, update `current_attempt_id`, compatibility lock fields, counters, event, and dispatch cursor, then return a detached `ClaimedJob` snapshot containing only primitives and validated payload data.

- [ ] **Step 4: Add fairness and every capacity-limit test**

```python
def test_claims_round_robin_across_scopes(pg_session_factory, registry) -> None:
    enqueue_many(pg_session_factory, workspace=A, count=5)
    enqueue_many(pg_session_factory, workspace=B, count=2)
    scope_order = [claim_scope(pg_session_factory, registry) for _ in range(4)]
    assert scope_order == [scope_key(A), scope_key(B), scope_key(A), scope_key(B)]


def test_busy_first_queue_does_not_starve_second_queue(pg_session_factory, registry) -> None:
    dispatcher = dispatcher_for_queues(pg_session_factory, registry, ["ingestion", "system"])
    enqueue_many(pg_session_factory, queue="ingestion", count=5)
    enqueue_many(pg_session_factory, queue="system", count=1)
    assert [dispatcher.claim_next(worker_id=uuid4()).queue_name for _ in range(2)] == [
        "ingestion", "system",
    ]


@pytest.mark.parametrize("limit_kind", ["queue", "workspace", "handler", "key"])
def test_claim_respects_capacity_under_race(limit_kind, pg_session_factory, registry) -> None:
    configure_limit(pg_session_factory, registry, kind=limit_kind, value=2)
    claims = run_concurrently(8, lambda index: claim_and_commit(
        pg_session_factory, registry, worker_id=uuid4()))
    assert len([claim for claim in claims if claim is not None]) == 2


@pytest.mark.parametrize("limit_kind", ["handler", "key"])
def test_shared_capacity_holds_across_two_queues(limit_kind, pg_session_factory, registry) -> None:
    enqueue_same_handler_in_two_queues(pg_session_factory, registry, limit_kind=limit_kind)
    claims = run_concurrently(2, lambda _: claim_any_queue(pg_session_factory, registry))
    assert len([claim for claim in claims if claim is not None]) == 1
```

- [ ] **Step 5: Implement capacity checks under the locked queue row**

Queue-global and queue/workspace count checks and the job claim happen while the queue row is locked. Handler/key advisory IDs are derived from SHA-256 namespaces and reduced to signed 64-bit integers; collisions may serialize unrelated work but can never admit excess work. Acquire multiple advisory IDs in ascending order and recheck fleet-wide counts after locking. Each dispatcher rotates the starting queue after every claim attempt so a permanently busy first queue cannot starve later configured queues. Priority applies within the selected scope only. System scope participates as `scope_key="system"`. Paused queues and unsupported handler versions return no claim and remain visible as queued/unroutable.

- [ ] **Step 6: Add stale-fencing tests before transition methods**

```python
def test_obsolete_attempt_cannot_heartbeat_or_complete(pg_session_factory, registry) -> None:
    first = claim_and_commit(pg_session_factory, registry, worker_id=uuid4())
    expire_and_requeue(pg_session_factory, first.attempt_id)
    second = claim_and_commit(pg_session_factory, registry, worker_id=uuid4())
    assert heartbeat(pg_session_factory, first) is False
    assert complete(pg_session_factory, first, result={}) is False
    assert heartbeat(pg_session_factory, second) is True
```

- [ ] **Step 7: Implement conditional heartbeat/progress/final update primitives**

Use `UPDATE ... WHERE jobs.current_attempt_id=:attempt_id AND jobs.status='running' RETURNING jobs.id`. Return `False`, never raise ownership success, when no row is updated. Rate-limit persisted progress using `JobAttempt.progress_updated_at`.

- [ ] **Step 8: Run real concurrency tests**

Run: `uv run pytest tests/integration/jobs/test_claims_pg.py -q`

Expected: PASS under eight concurrent claimant threads.

- [ ] **Step 9: Commit dispatch and fencing**

```bash
git add src/adaptive_rag/db/repositories/job_runtime.py src/adaptive_rag/jobs/dispatcher.py tests/unit/jobs/test_dispatcher.py tests/integration/jobs/test_claims_pg.py
git commit -m "feat(jobs): add fair fenced dispatch"
```

---

### Task 5: Complete transitions, cancellation, retry, unblock, and reaping

**Files:**
- Modify: `src/adaptive_rag/db/repositories/job_runtime.py`
- Modify: `src/adaptive_rag/jobs/service.py`
- Create: `src/adaptive_rag/jobs/reaper.py`
- Test: `tests/unit/jobs/test_transitions.py`
- Test: `tests/integration/jobs/test_reaper_pg.py`

**Interfaces:**
- Consumes: Task 4 fenced primitives and Task 2 error classes/retry policy.
- Produces: `JobTransitions.complete`, `retryable_failure`, `block`, `dead_letter`, `confirm_cancelled`; `JobReaper.run_once`; public service `cancel`, `retry`, `unblock`.

- [ ] **Step 1: Write a table-driven failing state-machine test**

```python
@pytest.mark.parametrize(
    "start,operation,end",
    [
        ("running", "complete", "succeeded"),
        ("running", "retryable_failure", "queued"),
        ("running", "block", "blocked"),
        ("running", "permanent_failure", "dead_letter"),
        ("queued", "cancel", "cancelled"),
        ("blocked", "unblock", "queued"),
        ("dead_letter", "retry", "queued"),
    ],
)
def test_allowed_transition_matrix(start: str, operation: str, end: str) -> None:
    assert transition_target(start, operation) == end
```

- [ ] **Step 2: Run transition tests and verify RED**

Run: `uv run pytest tests/unit/jobs/test_transitions.py -q`

Expected: import fails because `transition_target` and `JobTransitions` do not exist.

- [ ] **Step 3: Implement explicit transitions and structured events**

Every running transition requires the attempt token. Retryable failure increments `retry_count`, computes full jitter from an injected random source, and either sets `queued/run_after` or `dead_letter`. `BlockedJobError` does not increment `retry_count`. A manual dead-letter retry grants one execution and preserves the count unless `reset_retry_count=True`.

- [ ] **Step 4: Add cancellation-request behavior tests**

```python
def test_running_cancel_is_request_until_handler_confirms(session, running_job) -> None:
    job = service(session).cancel(running_job.id, actor=ADMIN)
    assert job.status == "running"
    assert job.cancellation_requested_at is not None
    assert event_types(session, job.id)[-1] == "cancel_requested"


def test_completion_after_cancel_request_is_success_with_audit(session, running_job) -> None:
    service(session).cancel(running_job.id, actor=ADMIN)
    transitions(session).complete(running_job.id, running_job.current_attempt_id, {})
    assert reload_job(session, running_job.id).status == "succeeded"
    assert event_types(session, running_job.id)[-1] == "completed_after_cancel_request"
```

- [ ] **Step 5: Implement cancel, retry, and unblock optimistic conflicts**

Queued/blocked cancellation is immediate. Running cancellation sets request fields. `retry` accepts only `dead_letter`; `unblock` accepts only `blocked`; stale status/version raises `JobStateConflictError` for API `409` mapping.

- [ ] **Step 6: Write expired-attempt race tests**

```python
def test_two_reapers_expire_one_attempt_once(pg_session_factory, registry) -> None:
    claim = expired_claim(pg_session_factory, registry)
    counts = run_concurrently(2, lambda _: reap_once(pg_session_factory, now=NOW))
    assert sum(counts) == 1
    assert event_types_for_job(pg_session_factory, claim.job_id).count("expired") == 1
```

- [ ] **Step 7: Implement bounded `SKIP LOCKED` reaping**

`JobReaper.run_once(now, batch_size=100)` selects expired current attempts, fences each conditionally, increments retry budget, requeues or dead-letters, clears compatibility locks, finishes attempt status `expired`, and emits one event.

- [ ] **Step 8: Run transition and reaper tests**

Run: `uv run pytest tests/unit/jobs/test_transitions.py tests/integration/jobs/test_reaper_pg.py -q`

Expected: PASS.

- [ ] **Step 9: Commit lifecycle behavior**

```bash
git add src/adaptive_rag/jobs src/adaptive_rag/db/repositories/job_runtime.py tests/unit/jobs/test_transitions.py tests/integration/jobs/test_reaper_pg.py
git commit -m "feat(jobs): add retry cancellation and recovery"
```

---

### Task 6: Build the general worker and migrate ingestion handlers

**Files:**
- Create: `src/adaptive_rag/jobs/worker.py`
- Create: `src/adaptive_rag/jobs/handlers.py`
- Modify: `src/adaptive_rag/ingestion/pipeline.py`
- Modify: `src/adaptive_rag/ingestion/indexing.py`
- Modify: `src/adaptive_rag/ingestion_ops.py`
- Modify: `src/adaptive_rag/config/settings.py`
- Modify: `src/adaptive_rag/db/session.py`
- Test: `tests/unit/jobs/test_worker.py`
- Modify: `tests/unit/config/test_settings.py`
- Test: `tests/integration/jobs/test_worker_pg.py`
- Test: `tests/unit/ingestion/test_ingestion_pipeline.py`
- Test: `tests/unit/ingestion/test_indexing_pipeline.py`
- Test: `tests/integration/api/test_ingestion_ops.py`

**Interfaces:**
- Consumes: `JobRegistry`, `JobDispatcher`, `JobTransitions`, `JobReaper`, session factory.
- Produces: async `JobWorker.run_once() -> WorkerRunReport`, `JobWorker.run()`, sync-only `JobWorker.run_once_sync()`, registered worker presence/heartbeat/drain state, PostgreSQL notification wakeups with polling fallback, registered `ingest_source@1` and `index_document_version@1` handlers; compatibility `run_next_ingestion_job` delegates to the worker.

- [ ] **Step 1: Write a failing worker test proving the lease is committed before execution**

```python
async def test_worker_commits_claim_before_invoking_handler(pg_session_factory, registry) -> None:
    entered = asyncio.Event()
    release = asyncio.Event()
    registry.register(blocking_async_definition(entered, release))
    job_id = enqueue_for_definition(pg_session_factory, registry)
    task = asyncio.create_task(worker(pg_session_factory, registry).run_once())
    await entered.wait()
    with pg_session_factory() as observer:
        job = observer.get(Job, job_id)
        assert job.status == "running"
        assert job.current_attempt_id is not None
    release.set()
    await task
```

- [ ] **Step 2: Run the worker test and verify RED**

Run: `uv run pytest tests/integration/jobs/test_worker_pg.py::test_worker_commits_claim_before_invoking_handler -q`

Expected: import fails because `JobWorker` is not defined.

- [ ] **Step 3: Implement async orchestration with independent database calls**

```python
class JobWorker:
    async def run_once(self) -> WorkerRunReport:
        claim = await asyncio.to_thread(self._claim_and_commit)
        if claim is None:
            return WorkerRunReport(status="idle")
        return await self._execute_claim(claim)

    def run_once_sync(self) -> WorkerRunReport:
        return asyncio.run(self.run_once())
```

`run_once_sync` is restricted to synchronous API/CLI compatibility call sites and raises a clear error if called from an active event loop. Async handlers are awaited. Sync handlers run through `asyncio.to_thread`. Attempt heartbeat is a sibling task that opens and commits its own session; when renewal fails before the configured safety margin, it cancels cooperative async work and fences sync-thread completion. Finalization opens a third session, validates/redacts the result, and enforces the 64 KiB cap. `max_concurrency` bounds local tasks; database limits remain authoritative.

`run()` upserts one `job_workers` presence row with process/application metadata and exact queues/handler versions, heartbeats it independently, and marks it draining before it stops claiming. Each replica also runs a bounded reaper tick on a configurable interval. Idle waiting uses a dedicated autocommit Psycopg connection with `LISTEN adaptive_rag_jobs`; timeout polling always calls the dispatcher even if no notification arrives. On graceful shutdown it keeps attempt heartbeats alive up to `drain_timeout`, then writes `shutdown_at`; a crash leaves presence stale and leases recover through the reaper.

Add optional `Settings.job_database_url`. `create_job_session_factory()` uses it for worker/scheduler control-plane transactions and falls back to `database_url` only for local compatibility. Handler resource factories remain explicit: ingestion may open its own normal application sessions, but no session object crosses a thread boundary.

- [ ] **Step 4: Add heartbeat-loss, cooperative cancellation, and drain tests**

```python
async def test_worker_refuses_completion_after_heartbeat_loses_fence(worker_fixture) -> None:
    worker_fixture.heartbeat_results.extend([True, False])
    report = await worker_fixture.worker.run_once()
    assert report.status == "fenced"
    assert worker_fixture.transitions.complete_calls == []


async def test_worker_drain_stops_claiming_and_waits_for_active_task(worker_fixture) -> None:
    await worker_fixture.start_one_blocked_handler()
    worker_fixture.worker.request_shutdown()
    assert worker_fixture.dispatcher.claim_calls == 1
    worker_fixture.release_handler()
    await worker_fixture.worker.wait_closed()
```

Add an integration assertion that a committed insert wakes an idle worker through `LISTEN/NOTIFY`, a rolled-back insert does not, and the poll timeout still finds work with notifications disabled. Assert that presence progresses `live -> draining -> shutdown` and that only one reaper replica wins an expired attempt.

- [ ] **Step 5: Separate ingestion domain work from queue transitions**

Extract `IngestionPipeline.process_source(workspace_id, source_id)` and `IndexingPipeline.index_document_version(workspace_id, document_version_id)` so they return existing result objects without calling `JobRepository.complete/block`. Keep `process_leased_job` as a compatibility wrapper until all old tests are migrated.

- [ ] **Step 6: Register ingestion handlers and preserve source idempotency**

`ingest_source@1` validates `source_id: UUID`, uses idempotency key `source:<uuid>`, and maps the existing blocked results to `BlockedJobError`. `index_document_version@1` validates `document_version_id: UUID`, uses `document-version:<uuid>`, and returns the existing count fields as result JSON.

- [ ] **Step 7: Make compatibility ingestion operations delegate without sharing sessions**

`enqueue_source_ingestion` calls `JobService.enqueue` in the caller session. `run_next_ingestion_job` must not execute using its route/session argument; it constructs `JobWorker` with `create_job_session_factory()`, applies the optional workspace filter, calls `run_once_sync`, and maps `WorkerRunReport` to `IngestionRunReport`. `run_ingestion_family_until_idle` repeats that same adapter and never holds the caller session across handler execution.

- [ ] **Step 8: Run worker and ingestion regression tests**

Run: `uv run pytest tests/unit/jobs/test_worker.py tests/integration/jobs/test_worker_pg.py tests/unit/config/test_settings.py tests/unit/ingestion/test_ingestion_pipeline.py tests/unit/ingestion/test_indexing_pipeline.py tests/integration/api/test_ingestion_ops.py -q`

Expected: PASS, including existing contributor authorization and response fields.

- [ ] **Step 9: Commit the worker migration**

```bash
git add src/adaptive_rag/jobs src/adaptive_rag/ingestion src/adaptive_rag/ingestion_ops.py src/adaptive_rag/config/settings.py src/adaptive_rag/db/session.py tests/unit/jobs tests/integration/jobs/test_worker_pg.py tests/unit/config/test_settings.py tests/unit/ingestion tests/integration/api/test_ingestion_ops.py
git commit -m "feat(jobs): run ingestion through general workers"
```

---

### Task 7: Add durable cron scheduling and migrate system maintenance

**Files:**
- Modify: `pyproject.toml`
- Modify: `uv.lock`
- Create: `src/adaptive_rag/db/repositories/job_schedules.py`
- Create: `src/adaptive_rag/jobs/scheduler.py`
- Create: `src/adaptive_rag/jobs/schedule_service.py`
- Modify: `src/adaptive_rag/jobs/handlers.py`
- Modify: `src/adaptive_rag/system_scheduler.py`
- Modify: `src/adaptive_rag/api/routes/provider_connections.py`
- Test: `tests/unit/jobs/test_cron_schedule.py`
- Test: `tests/integration/jobs/test_scheduler_pg.py`
- Test: `tests/unit/test_system_scheduler.py`
- Test: `tests/integration/api/test_provider_connections.py`

**Interfaces:**
- Consumes: `JobSchedule`, `JobService.enqueue`, handler registry, existing provider pricing sync.
- Produces: `schedule_occurrences`, `JobScheduler.run_once`, `JobScheduleService` CRUD/action methods, `provider_model_pricing_sync@1` system handler and schedule compatibility projections.

- [ ] **Step 1: Add failing cron, DST, and misfire tests**

```python
def test_spring_forward_nonexistent_local_time_is_skipped() -> None:
    occurrences = schedule_occurrences(
        expression="30 2 * * *", timezone="America/New_York",
        after_utc=datetime(2026, 3, 7, tzinfo=UTC),
        through_utc=datetime(2026, 3, 9, tzinfo=UTC), limit=10,
    )
    assert [value.astimezone(ZoneInfo("America/New_York")).day
            for value in occurrences] == [7, 9]


def test_run_once_returns_only_latest_missed_occurrence() -> None:
    assert apply_misfire_policy(MISSED, "run_once", max_catch_up=10) == [MISSED[-1]]
```

- [ ] **Step 2: Run cron tests and verify RED**

Run: `uv run pytest tests/unit/jobs/test_cron_schedule.py -q`

Expected: import fails because `adaptive_rag.jobs.scheduler` does not exist.

- [ ] **Step 3: Add the verified cron dependency**

Run: `uv add 'croniter>=6.2.4,<7' && uv add --dev 'types-croniter>=6.2.2.20260518'`

Expected: `pyproject.toml` and `uv.lock` update without unrelated dependency removals.

- [ ] **Step 4: Implement five-field validation and timezone-aware occurrences**

Reject second/year fields, aliases outside the supported grammar, invalid IANA zones, `max_catch_up` outside `1..100`, and occurrence loops above 100 per tick. Normalize every returned instant to UTC and explicitly test both DST directions.

- [ ] **Step 5: Write the replicated scheduler race test**

```python
def test_two_schedulers_create_one_job_per_occurrence(pg_session_factory, registry) -> None:
    schedule = create_due_schedule(pg_session_factory, scope="system")
    counts = run_concurrently(2, lambda _: scheduler_once(pg_session_factory, registry))
    assert sum(counts) == 1
    assert count_jobs_for_occurrence(pg_session_factory, schedule.id, schedule.next_run_at) == 1
```

- [ ] **Step 6: Implement schedule repository and replicated scheduler loop**

Select due schedules in batches with `FOR UPDATE SKIP LOCKED`; compute `skip`, `run_once`, or bounded `catch_up`; create jobs and update `next_run_at` in the same transaction. `JobScheduleService` validates handler opt-in/scope, payload, queue existence, timezone/cron/misfire bounds, and optimistic version for create/edit/pause/resume/archive/run-now. `run-now` links a job to the schedule with `scheduled_for=None` and does not move the cron cursor. `DELETE` sets `archived_at`.

- [ ] **Step 7: Register and migrate provider pricing maintenance**

Register `provider_model_pricing_sync@1` as `scope="system"`, queue `system`, manual enqueue allowed only to superadmin. Seed a daily UTC schedule. Compatibility `system_scheduler` and `/runtime-settings/system-tasks` read the schedule and latest job/attempt; `run-pricing-sync` delegates to `run-now` except `--dry-run`, which remains inline and non-persistent.

- [ ] **Step 8: Run scheduler and compatibility tests**

Run: `uv run pytest tests/unit/jobs/test_cron_schedule.py tests/integration/jobs/test_scheduler_pg.py tests/unit/test_system_scheduler.py tests/integration/api/test_provider_connections.py -q`

Expected: PASS; concurrent scheduler count is one.

- [ ] **Step 9: Commit scheduling**

```bash
git add pyproject.toml uv.lock src/adaptive_rag/jobs src/adaptive_rag/db/repositories/job_schedules.py src/adaptive_rag/system_scheduler.py src/adaptive_rag/api/routes/provider_connections.py tests/unit/jobs/test_cron_schedule.py tests/integration/jobs/test_scheduler_pg.py tests/unit/test_system_scheduler.py tests/integration/api/test_provider_connections.py
git commit -m "feat(jobs): add durable cron schedules"
```

---

### Task 8: Expose workspace and global administrative APIs

**Files:**
- Create: `src/adaptive_rag/api/schemas/jobs.py`
- Create: `src/adaptive_rag/api/routes/jobs.py`
- Create: `src/adaptive_rag/jobs/metrics.py`
- Modify: `src/adaptive_rag/jobs/service.py`
- Modify: `src/adaptive_rag/api/app.py`
- Modify: `src/adaptive_rag/api/dependencies.py`
- Modify: `src/adaptive_rag/api/schemas/ingestion_ops.py`
- Modify: `src/adaptive_rag/api/routes/ingestion_ops.py`
- Test: `tests/integration/api/test_jobs_api.py`
- Test: `tests/integration/api/test_job_schedules_api.py`
- Test: `tests/integration/api/test_ingestion_ops.py`
- Test: `tests/unit/test_api_hard_caps.py`

**Interfaces:**
- Consumes: `JobService`, `JobScheduleService`, registry, current auth dependencies.
- Produces: typed workspace job/schedule/handler endpoints, superadmin queue/worker/system endpoints, bounded `JobMetricsService.snapshot`, compatibility response projection.

- [ ] **Step 1: Write failing RBAC and scope-isolation API tests**

```python
def test_generic_mutations_require_workspace_admin(client, workspace, users) -> None:
    body = {"job_type": "manual_echo", "handler_version": 1,
            "payload": {"message": "hi"}}
    assert post_as(client, users.viewer, workspace_jobs(workspace), body).status_code == 403
    assert post_as(client, users.contributor, workspace_jobs(workspace), body).status_code == 403
    assert post_as(client, users.admin, workspace_jobs(workspace), body).status_code == 201


def test_system_jobs_are_superadmin_only(client, users) -> None:
    assert get_as(client, users.workspace_admin, "/admin/jobs?scope=system").status_code == 403
    assert get_as(client, users.superadmin, "/admin/jobs?scope=system").status_code == 200
```

- [ ] **Step 2: Run API tests and verify RED**

Run: `uv run pytest tests/integration/api/test_jobs_api.py tests/integration/api/test_job_schedules_api.py -q`

Expected: 404 because the generic routes are not registered.

- [ ] **Step 3: Implement bounded request/response schemas**

Create `BackgroundJobResponse`, `JobAttemptResponse`, `JobEventResponse`, `JobDetailResponse`, `JobPageResponse`, `JobScheduleResponse`, `JobQueueResponse`, `JobWorkerResponse`, and mutation bodies. Use Pydantic bounds matching Global Constraints and safe error objects `{code, message, trace_id}`.

- [ ] **Step 4: Implement workspace routes and optimistic conflicts**

Add the approved `GET/POST jobs`, detail, cancel, retry, unblock, schedule CRUD, pause/resume/run-now endpoints plus `GET /workspaces/{workspace_id}/job-handlers`. Reads depend on `get_workspace_access`; mutations depend on `get_workspace_admin_access`. Handler discovery returns only registered workspace-scope definitions opted into manual use and allowed for the caller's role. Enqueue and schedule creation independently enforce the same registry rule server-side. Enqueue returns `201` with `created=true` for a new job and `200` with `created=false` for an idempotent reuse; return `409` for idempotency/state/version conflicts and stable cursor links.

- [ ] **Step 5: Implement superadmin routes and snapshot metrics**

Add `/admin/jobs`, `/admin/job-queues`, `/admin/job-queues/{name}`, `/admin/job-workers`, `/admin/job-handlers`, and `/admin/job-metrics`. Extend `JobService` with queue read/pause/resume/configure and worker-presence read methods so CLI and API do not mutate repositories directly. `JobMetricsService` returns queue depth, oldest eligible age, running/capacity, retry/block/dead-letter/unroutable counts, worker states, and scheduler lag from bounded aggregate queries. A worker is stale when its last heartbeat is older than 30 seconds; an eligible queued job is unroutable when no non-stale worker advertises its queue and exact handler version.

- [ ] **Step 6: Preserve compatibility projections and contributor exception**

Existing ingestion routes keep contributor dependencies and response fields. `locked_by/locked_until` project from current attempt; `attempts/max_attempts` project from compatibility columns maintained by transitions. The old `run-next` endpoint delegates to a filtered one-shot general worker.

- [ ] **Step 7: Add pagination, redaction, stale-operation, and cap tests**

```python
def test_job_detail_redacts_handler_fields(client, workspace_admin, secret_job) -> None:
    response = get_as(client, workspace_admin, job_detail_url(secret_job))
    assert response.json()["job"]["payload_json"]["api_key"] == "[REDACTED]"


def test_stale_schedule_version_returns_conflict(client, workspace_admin, schedule) -> None:
    response = patch_as(client, workspace_admin, schedule_url(schedule),
                        {"version": schedule.version - 1, "paused": True})
    assert response.status_code == 409
```

- [ ] **Step 8: Run all job APIs and ingestion regressions**

Run: `uv run pytest tests/integration/api/test_jobs_api.py tests/integration/api/test_job_schedules_api.py tests/integration/api/test_ingestion_ops.py tests/unit/test_api_hard_caps.py -q`

Expected: PASS.

- [ ] **Step 9: Commit the control-plane API**

```bash
git add src/adaptive_rag/api src/adaptive_rag/jobs/service.py src/adaptive_rag/jobs/metrics.py tests/integration/api/test_jobs_api.py tests/integration/api/test_job_schedules_api.py tests/integration/api/test_ingestion_ops.py tests/unit/test_api_hard_caps.py
git commit -m "feat(api): expose background job operations"
```

---

### Task 9: Expand CLI and Compose while preserving aliases

**Files:**
- Modify: `src/adaptive_rag/cli/jobs.py`
- Modify: `src/adaptive_rag/cli/system.py`
- Modify: `compose.yaml`
- Modify: `.env.example`
- Test: `tests/integration/cli/test_jobs_cli.py`
- Test: `tests/integration/cli/test_cli.py`
- Test: `tests/integration/cli/test_provider_cli.py`

**Interfaces:**
- Consumes: general services, `JobWorker`, `JobScheduler`, compatibility system task adapter.
- Produces: commands listed in the approved spec and global Compose worker/scheduler services.

- [ ] **Step 1: Add failing CLI command-registration tests**

```python
@pytest.mark.parametrize("args", [
    ["jobs", "worker", "--once"],
    ["jobs", "schedules", "list", "--workspace-id", str(WORKSPACE_ID)],
    ["jobs", "queues", "list"],
    ["jobs", "workers", "list"],
])
def test_general_job_commands_exist(args: list[str]) -> None:
    result = runner.invoke(app, args)
    assert result.exit_code != 2
```

- [ ] **Step 2: Run CLI registration tests and verify RED**

Run: `uv run pytest tests/integration/cli/test_jobs_cli.py -q`

Expected: FAIL with unknown commands for `worker`, `schedules`, `queues`, and `workers`.

- [ ] **Step 3: Split CLI command groups without breaking root registration**

Keep `jobs.py` as the root Typer module and add child typers `schedules_app`, `queues_app`, and `workers_app`. Implement JSON commands `enqueue`, `list`, `show`, `cancel`, `retry`, `unblock`, `worker`, scheduler CRUD/actions, queue operations, and worker list. Validate JSON payload from `--payload-json` before opening a transaction.

- [ ] **Step 4: Keep ingestion and system aliases exact**

`enqueue-ingest-source`, `run-worker --workspace-id`, `system run-scheduler`, `system list-tasks`, and `system run-pricing-sync` remain callable. Their tests assert the same keys and exit codes while execution delegates to the new services.

- [ ] **Step 5: Change Compose to global workers and general scheduler**

Worker command becomes `adaptive-rag jobs worker --queues ingestion,default,system`; remove the hard requirement for `ADAPTIVE_RAG_WORKER_WORKSPACE_ID`. Scheduler command becomes `adaptive-rag jobs scheduler --poll-interval-seconds 30`. Add health-oriented `--once` commands to the runbook rather than container health checks that would process arbitrary work.

Compose passes `ADAPTIVE_RAG_JOB_DATABASE_URL` separately to worker and scheduler, with the local demo value allowed to match the application user. `.env.example` documents that production must use a non-owner role with DML/sequence access required by registered handlers and no schema ownership, `CREATE`, or Alembic privileges; Task 12 verifies and documents the exact grants.

- [ ] **Step 6: Run CLI and Compose contract tests**

Run: `uv run pytest tests/integration/cli/test_jobs_cli.py tests/integration/cli/test_cli.py tests/integration/cli/test_provider_cli.py tests/unit/test_acceptance_docs.py -q && docker compose config -q`

Expected: PASS and valid Compose configuration.

- [ ] **Step 7: Commit CLI and deployment wiring**

```bash
git add src/adaptive_rag/cli compose.yaml .env.example tests/integration/cli tests/unit/test_acceptance_docs.py
git commit -m "feat(jobs): add worker scheduler and operator CLI"
```

---

### Task 10: Add frontend API types, client methods, and navigation state

**Files:**
- Modify: `frontend/src/lib/apiClient.ts`
- Modify: `frontend/src/lib/apiClient.test.ts`
- Create: `frontend/src/features/jobs/jobPlatformUi.ts`
- Create: `frontend/src/features/jobs/jobPlatformUi.test.ts`
- Modify: `frontend/src/features/shell/AppShell.tsx`
- Modify: `frontend/src/features/shell/AppShell.test.tsx`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/App.test.tsx`

**Interfaces:**
- Consumes: Task 8 JSON contracts and existing settings navigation patterns.
- Produces: TypeScript `BackgroundJob`, `JobSchedule`, `JobQueue`, `JobWorker`, pages/details and API methods; `JobsSubmodule = 'jobs'|'schedules'|'queues'|'workers'`; `/settings/jobs/*` navigation.

- [ ] **Step 1: Write failing API-client URL/body tests**

```typescript
test('lists jobs with stable filters and mutates one job', async () => {
  await client.listBackgroundJobs(workspaceId, {
    status: 'running', queue: 'ingestion', limit: 50, cursor: 'next',
  })
  await client.cancelBackgroundJob(workspaceId, jobId, { version: 3 })
  expect(requests[0].url).toContain(
    `/workspaces/${workspaceId}/jobs?status=running&queue=ingestion&limit=50&cursor=next`,
  )
  expect(requests[1].url).toContain(`/workspaces/${workspaceId}/jobs/${jobId}/cancel`)
})
```

- [ ] **Step 2: Run frontend client tests and verify RED**

Run: `cd frontend && pnpm test -- src/lib/apiClient.test.ts`

Expected: TypeScript compile failure because the background-job methods are missing.

- [ ] **Step 3: Add exact API types and client methods**

Implement workspace job/detail/actions, schedule CRUD/actions, and superadmin queue/worker/metrics methods. Reuse the existing request/error plumbing and omit null filters from query strings.

- [ ] **Step 4: Add failing pure UI-helper tests**

```typescript
test('encodes and decodes job filters in the URL', () => {
  const query = encodeJobFilters({ status: 'dead_letter', queue: 'system', cursor: null })
  expect(query).toBe('status=dead_letter&queue=system')
  expect(decodeJobFilters(query).status).toBe('dead_letter')
})

test('only actionable states expose their operations', () => {
  expect(jobActions('blocked', true)).toEqual(['unblock', 'cancel'])
  expect(jobActions('dead_letter', true)).toEqual(['retry'])
  expect(jobActions('running', false)).toEqual([])
})
```

- [ ] **Step 5: Implement URL filters, labels, tones, and action guards**

Keep these helpers pure. Unknown statuses use a neutral badge and no mutation actions. Admin capability is an explicit boolean from current workspace/system role.

- [ ] **Step 6: Add Background Jobs settings navigation**

Add module `jobs` with submodules `jobs`, `schedules`, `queues`, `workers`; route each to `/settings/jobs/<submodule>`. Jobs and Schedules are visible for workspace readers; Queues and Workers appear only for superadmins, and direct unauthorized routes resolve to the first allowed submodule without issuing global API calls. Ensure mobile sidebar labels, keyboard selection, route restoration, and existing module types remain exhaustive.

- [ ] **Step 7: Run client/navigation/helper tests**

Run: `cd frontend && pnpm test -- src/lib/apiClient.test.ts src/features/jobs/jobPlatformUi.test.ts src/features/shell/AppShell.test.tsx src/App.test.tsx`

Expected: PASS.

- [ ] **Step 8: Commit frontend contracts and navigation**

```bash
git add frontend/src/lib frontend/src/features/jobs/jobPlatformUi.ts frontend/src/features/jobs/jobPlatformUi.test.ts frontend/src/features/shell frontend/src/App.tsx frontend/src/App.test.tsx
git commit -m "feat(frontend): add job platform navigation"
```

---

### Task 11: Build the Background Jobs console

**Files:**
- Create: `frontend/src/features/jobs/JobPlatformView.tsx`
- Create: `frontend/src/features/jobs/JobPlatformView.test.tsx`
- Create: `frontend/src/features/jobs/JobDetailDrawer.tsx`
- Create: `frontend/src/features/jobs/JobDetailDrawer.test.tsx`
- Modify: `frontend/src/App.tsx`
- Test: `frontend/src/App.test.tsx`

**Interfaces:**
- Consumes: Task 10 client/types/navigation and existing `Panel`, `Table`, `Tabs`, `Badge`, `Button`, `Select`, `Callout`, `EmptyState`, toast provider.
- Produces: jobs/schedules/queues/workers views, detail drawer, polling lifecycle, confirmations, and authorized mutations.

- [ ] **Step 1: Write the failing Jobs table/detail test**

```typescript
test('filters jobs and opens an attempt/event detail drawer', async () => {
  render(<JobPlatformPanel {...propsWithJobs()} activeSubmodule="jobs" />)
  await userEvent.selectOptions(screen.getByLabelText('Status'), 'running')
  await userEvent.click(screen.getByRole('button', { name: /index_document_version/i }))
  expect(props.onFiltersChange).toHaveBeenCalledWith(expect.objectContaining({ status: 'running' }))
  expect(await screen.findByRole('dialog', { name: /job details/i })).toHaveTextContent('leased')
  expect(screen.getByText('[REDACTED]')).toBeInTheDocument()
})
```

- [ ] **Step 2: Run the panel test and verify RED**

Run: `cd frontend && pnpm test -- src/features/jobs/JobPlatformView.test.tsx`

Expected: import fails because `JobPlatformView.tsx` does not exist.

- [ ] **Step 3: Implement summary, filter bar, paginated table, and drawer**

Use semantic tables and buttons, stable status badges, empty/loading/error states, cursor next/previous controls, and a focus-trapped drawer showing redacted payload/result, progress, attempts, events, trace IDs, and timestamps.

- [ ] **Step 4: Add failing mutation and RBAC tests**

```typescript
test('admin confirms cancel and receives toast feedback', async () => {
  const props = adminProps()
  render(<JobPlatformPanel {...props} activeSubmodule="jobs" />)
  await userEvent.click(screen.getByRole('button', { name: 'Cancel Job' }))
  await userEvent.click(screen.getByRole('button', { name: 'Confirm Cancellation' }))
  expect(props.onCancel).toHaveBeenCalledWith(JOB_ID, JOB_VERSION)
})

test('viewer never sees mutation controls', () => {
  render(<JobPlatformPanel {...viewerProps()} activeSubmodule="jobs" />)
  expect(screen.queryByRole('button', { name: /cancel|retry|unblock/i })).toBeNull()
})
```

- [ ] **Step 5: Implement jobs and schedules mutations with stale-state recovery**

Confirmation dialogs precede cancellation, retry reset, schedule archive, and queue pause. On `409`, refresh the affected record and show an operator-safe toast. Durable error/progress context remains inline.

- [ ] **Step 6: Implement Schedules, Queues, and Workers tabs**

Schedules show cron, timezone, policy, next/last times and pause/resume/run-now/edit/archive. Queues show depth, capacity and pause/configure actions to superadmins. Workers show live/stale/draining state, heartbeat age, version, queues, supported handlers, and active attempts.

- [ ] **Step 7: Add visibility-aware polling tests and implementation**

```typescript
test('polls only while the document is visible and cleans up on unmount', () => {
  vi.useFakeTimers()
  const { unmount } = render(<ConnectedJobPlatform {...props} />)
  vi.advanceTimersByTime(10_000)
  expect(props.client.listBackgroundJobs).toHaveBeenCalledTimes(3)
  setDocumentVisibility('hidden')
  vi.advanceTimersByTime(10_000)
  expect(props.client.listBackgroundJobs).toHaveBeenCalledTimes(3)
  unmount()
  expect(vi.getTimerCount()).toBe(0)
})
```

Poll every five seconds only when visible. Fetch detail only while its drawer is open. Abort obsolete requests with `AbortController`.

- [ ] **Step 8: Wire App state and run frontend verification**

Run: `cd frontend && pnpm test -- src/features/jobs src/App.test.tsx && pnpm lint && pnpm build`

Expected: all tests, lint, and build PASS.

- [ ] **Step 9: Commit the console**

```bash
git add frontend/src/features/jobs frontend/src/App.tsx frontend/src/App.test.tsx
git commit -m "feat(frontend): add background jobs console"
```

---

### Task 12: Add fault-injection acceptance, observability, retention, and runbook

**Files:**
- Modify: `src/adaptive_rag/jobs/metrics.py`
- Create: `src/adaptive_rag/jobs/retention.py`
- Create: `tests/integration/jobs/test_fault_recovery_pg.py`
- Create: `tests/integration/jobs/test_acceptance_pg.py`
- Create: `tests/integration/jobs/test_retention_pg.py`
- Create: `docs/architecture/job-platform-runbook.md`
- Modify: `README.md`
- Modify: `docs/architecture/v1-release-package.md`
- Modify: `openspec/specs/job-queue/spec.md`
- Modify: `openspec/specs/ingestion-ops-surface/spec.md`
- Modify: `openspec/specs/chat-frontend/spec.md`
- Test: `tests/unit/test_acceptance_docs.py`
- Test: `tests/integration/cli/test_v1_quality_gate_cli.py`

**Interfaces:**
- Consumes: the complete runtime/control plane from Tasks 1-11.
- Produces: verified 500-job acceptance evidence, recovery tests, retention policy, current OpenSpec truth, and deployment/recovery runbook.

- [ ] **Step 1: Write fault-injection tests before recovery harnesses**

```python
def test_sigkill_worker_requeues_and_fences_old_attempt(postgres_stack) -> None:
    job_id = postgres_stack.enqueue("blocking_test", idempotency_key="kill-me")
    old_attempt = postgres_stack.start_worker_and_wait_for_running(job_id)
    postgres_stack.sigkill_worker()
    postgres_stack.advance_or_wait_for_lease_expiry(job_id)
    postgres_stack.run_reaper_once()
    new_attempt = postgres_stack.start_worker_and_wait_for_terminal(job_id)
    assert new_attempt != old_attempt
    assert postgres_stack.try_complete(job_id, old_attempt) is False
    assert postgres_stack.job(job_id).status == "succeeded"


def test_polling_recovers_when_notifications_are_disabled(postgres_stack) -> None:
    postgres_stack.disable_job_notifications()
    job_id = postgres_stack.enqueue("echo")
    assert postgres_stack.worker(poll_seconds=0.1).wait_for_terminal(job_id).status == "succeeded"


def test_worker_database_role_cannot_create_schema_objects(postgres_stack) -> None:
    with pytest.raises(ProgrammingError):
        postgres_stack.worker_connection.execute(text("CREATE TABLE forbidden_worker_ddl(id int)"))
```

- [ ] **Step 2: Run fault tests and verify RED**

Run: `uv run pytest tests/integration/jobs/test_fault_recovery_pg.py -q`

Expected: FAIL because the process harness and notification controls are not implemented.

- [ ] **Step 3: Implement subprocess worker/scheduler harness and pass fault tests**

Use `subprocess.Popen` with explicit database URL and worker IDs, readiness by database state, `os.kill(pid, signal.SIGKILL)`, and bounded polling deadlines. Always terminate child processes in fixture finalizers.

- [ ] **Step 4: Write and implement metrics/retention tests**

Metrics snapshots must bound queries and expose the approved counts/ages. Retention deletes terminal jobs only when older than policy and not protected by provider usage or another audit reference; attempts/events delete in the same transaction. A dry-run returns IDs/counts without mutation. The PostgreSQL fixture creates a non-owner worker role using the runbook grants, proves normal enqueue/claim/heartbeat/finalization plus registered handler data access, and proves schema DDL/migration-table writes are denied.

- [ ] **Step 5: Add the 500-job, four-scope acceptance test**

```python
def test_500_jobs_complete_without_loss_starvation_or_limit_breach(postgres_stack) -> None:
    job_ids = postgres_stack.enqueue_matrix(workspaces=4, jobs_per_workspace=125)
    evidence = postgres_stack.run_workers(count=4, max_concurrency=8).drain(job_ids)
    assert evidence.terminal_job_ids == set(job_ids)
    assert evidence.duplicate_finalizations == 0
    assert evidence.max_running_by_queue <= evidence.queue_limit
    assert all(evidence.first_start_by_workspace.values())
```

- [ ] **Step 6: Run acceptance and record non-gating benchmark evidence**

Run: `uv run pytest tests/integration/jobs/test_acceptance_pg.py tests/integration/jobs/test_fault_recovery_pg.py tests/integration/jobs/test_retention_pg.py -q -s`

Expected: PASS and print queue latency, duration, connection high-water mark, and transaction-age evidence without wall-clock assertions.

- [ ] **Step 7: Update canonical specs and operational documentation**

Document schema migration, global worker/scheduler Compose commands, queue pause/recovery, stale worker/fence diagnosis, retry/dead-letter operations, scheduler misfires/DST, metrics, retention dry-run/apply, rollback limits, and compatibility commands. Update OpenSpec requirements to match the implemented general platform and console.

- [ ] **Step 8: Run the full backend/frontend/release verification**

Run:

```bash
uv run ruff check .
uv run mypy src/adaptive_rag
uv run pytest -q
uv run alembic heads
docker compose config -q
cd frontend && pnpm test && pnpm lint && pnpm build
```

Expected: every command exits zero, Alembic has one head, and no test emits an unexpected warning.

- [ ] **Step 9: Run the Docker Compose smoke**

Run:

```bash
docker compose up -d postgres
docker compose run --rm api uv run alembic upgrade head
docker compose run --rm worker adaptive-rag jobs worker --once
docker compose run --rm scheduler adaptive-rag jobs scheduler --once
docker compose down
```

Expected: migration succeeds; worker and scheduler emit valid JSON status; Compose shuts down cleanly. The named Postgres volume is retained unless the user separately authorizes `docker compose down -v`.

- [ ] **Step 10: Commit acceptance and runbook**

```bash
git add src/adaptive_rag/jobs tests/integration/jobs docs README.md openspec/specs
git commit -m "test(jobs): verify queue platform end to end"
```

---

## Specification Coverage Map

- Goals, boundaries, handler contract, and resource/security limits: Global Constraints plus Tasks 2, 3, and 6.
- Persistence model, migration, compatibility UUIDs, workspace/system scope, and transactional notifications: Task 1.
- Idempotency, pagination, redaction, state machine, cancellation, retry, unblock, leases, fencing, fairness, capacity, and recovery: Tasks 3-6.
- Durable cron, IANA/DST behavior, misfires, replicated scheduling, and provider-pricing migration: Task 7.
- Workspace/global RBAC, API, CLI, Compose, and compatibility surfaces: Tasks 8 and 9.
- Jobs, Schedules, Queues, and Workers console with URL filters, polling, confirmations, and toast feedback: Tasks 10 and 11.
- Metrics, unroutable work, worker presence, retention, fault injection, 500-job acceptance, runbook, and canonical OpenSpec updates: Tasks 6, 8, and 12.

Every completion criterion in the approved design is represented by at least one focused test and one final verification command above.

## Final Verification Checklist

- [ ] `git diff --check` is clean.
- [ ] `uv run alembic heads` reports only `p5q6r7s8t9u0`.
- [ ] Focused RED/GREEN evidence was observed for every task.
- [ ] Full Ruff, MyPy, pytest, Vitest, frontend lint/build, and Compose config pass.
- [ ] Real PostgreSQL tests prove idempotency, fairness, limits, fencing, reaping, scheduling, and transaction rollback.
- [ ] Fault tests prove SIGKILL recovery and polling fallback.
- [ ] Existing ingestion and provider-pricing compatibility tests pass.
- [ ] Console permissions and redaction tests cover superadmin, workspace admin, contributor, and viewer.
- [ ] Runbook and OpenSpec reflect the delivered behavior.
- [ ] `git status --short` contains no unreviewed generated files or unrelated user changes.
