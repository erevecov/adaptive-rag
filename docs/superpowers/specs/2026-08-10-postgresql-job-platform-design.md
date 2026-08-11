# PostgreSQL Job Platform Design

**Date:** 2026-08-10  
**Status:** Design approved; written specification pending user review  
**Scope:** General-purpose background job queue, durable scheduler, worker fleet,
operational API/CLI, and web console for Adaptive RAG.

## Decision

Adaptive RAG will evolve its existing PostgreSQL-backed `jobs` subsystem into an
application-owned background job platform. PostgreSQL remains the only durable
coordination service and the existing workspace-scoped job identity remains the
public source of truth.

The platform will not adopt PgQueuer or Procrastinate as its runtime engine. Both
libraries solve important dispatch concerns, but neither replaces Adaptive RAG's
workspace isolation, UUID job identity, `blocked` and `dead_letter` semantics,
append-only audit contract, provider-usage references, RBAC, or existing API and
frontend behavior. A hybrid would introduce a second mutable job state without
removing the domain-specific state.

The platform provides at-least-once execution. It does not claim exactly-once
effects. Database fencing prevents an obsolete worker from changing canonical
job state, while handler idempotency protects business and external side effects.

## Goals

- Support any registered Adaptive RAG background handler, not only ingestion.
- Enqueue jobs atomically with application data in the caller's transaction.
- Run one global worker fleet across workspaces with fair dispatch.
- Enforce concurrency globally, per queue, per workspace, per handler, and for an
  optional handler-provided concurrency key.
- Keep claim transactions short and execute handlers outside database locks.
- Recover automatically from process death, lost connections, and expired leases.
- Reject stale heartbeat and completion writes through an attempt fencing token.
- Provide delayed jobs, retry backoff, dead letters, blocking, cancellation, and
  manual retry/unblock operations.
- Provide durable cron schedules with explicit time zones and misfire policies.
- Preserve an append-only workspace-scoped event history and structured attempt
  history.
- Expose a workspace API, a global administrative API, CLI commands, and a web
  console for jobs, schedules, queues, and workers.
- Preserve the existing ingestion API, CLI commands, UI behavior, and job UUIDs.
- Verify correctness against real PostgreSQL under concurrent claims and injected
  worker failures.

## Non-goals

- Executing shell commands, arbitrary Python, or payload-selected imports.
- Loading untrusted handler code or installing worker plugins at runtime.
- Exactly-once external side effects.
- Persisting secrets in job payloads, results, errors, or event metadata.
- Storing large artifacts in the queue. Jobs may reference artifacts stored by an
  owning subsystem.
- A cross-region broker or a replacement for high-volume event streaming.
- CPU-process isolation in the first implementation. CPU-heavy work must delegate
  to a dedicated service or be added as a separately designed executor later.

## Architectural boundaries

### Handler registry

Handlers are registered in application code under a stable name and integer
version. A registration declares:

- Pydantic payload model;
- sync or async callable;
- default queue and priority;
- retry policy and lease duration;
- concurrency limits and optional concurrency-key derivation;
- whether generic manual enqueue is allowed and its minimum workspace role;
- payload, result, and error redaction policy.

The API and scheduler can enqueue only a registered handler/version pair. Workers
claim only handler versions supported by their local registry. A payload cannot
name an import path, module, callable, or executor.

The worker orchestration loop is asynchronous. Async handlers run on the event
loop; sync handlers run in a bounded thread pool. Every handler execution creates
its own application session or uses explicitly injected resources. No SQLAlchemy
session crosses thread boundaries.

### Job service

The job service owns enqueue, inspection, transitions, cancellation, retry,
unblock, progress, and result persistence. Producers call this service with their
existing SQLAlchemy session so the business write and job insert commit or roll
back together.

### Dispatcher and worker

The dispatcher claims work in a short transaction, commits the lease, and then
invokes the handler. Heartbeats and final transitions use independent short
transactions. Workers listen for PostgreSQL notifications and retain timed
polling as the correctness fallback.

### Scheduler

Scheduler replicas expand due cron occurrences into normal jobs. PostgreSQL row
locking and a unique occurrence constraint make the scheduler safe to replicate;
there is no permanent leader.

### Reaper

Reaper replicas scan expired attempts in bounded batches. A reaper expires an
attempt only while it remains the job's current attempt. It then requeues the job
with backoff or moves it to `dead_letter` when retry budget is exhausted.

### Control plane

FastAPI, Typer, and the React console call the same application services. UI
visibility never substitutes for backend authorization. Domain-specific ingestion
views remain projections over the general job API.

## Persistence model

All identifiers are UUIDs unless otherwise stated. All timestamps are timezone-
aware and stored in UTC.

### `jobs`

`jobs` remains the canonical public record. Existing rows and identifiers are
preserved. The model contains:

- `id`, `workspace_id`;
- `queue_name` and stable `job_type` handler name;
- `handler_version`;
- `status`;
- `priority`;
- validated `payload_json`;
- optional `result_json`, limited to 64 KiB after serialization;
- optional `idempotency_key`;
- `run_after`;
- `attempt_count`, counting every successful claim;
- `retry_count`, counting retryable failures and expired attempts;
- `max_retries`;
- optional `current_attempt_id` fencing reference;
- optional `schedule_id` and `scheduled_for`;
- optional `concurrency_key`;
- optional `cancellation_requested_at` and requesting actor;
- safe `last_error_code`, `last_error_message`, and `last_trace_id`;
- `created_at`, `updated_at`, and terminal `finished_at`.

Public compatibility aliases preserve the current `attempts` and `max_attempts`
response fields during migration. New clients use `attempt_count`, `retry_count`,
and `max_retries`, which remove the current ambiguity between executions and retry
budget.

An open-job partial unique constraint enforces idempotency for non-null keys:

```text
(workspace_id, job_type, handler_version, idempotency_key)
WHERE status IN ('queued', 'running', 'blocked')
```

This key prevents concurrent duplicate enqueue. A terminal job releases the key
so a future operation may intentionally reuse it. A caller that requires lifetime
deduplication must use a domain-owned unique record rather than queue state.

On an open-key conflict, enqueue compares the canonical payload, queue, priority,
and `run_after`. Matching requests return the existing job and report
`created=false`. A differing request returns `409 idempotency_conflict`; it never
silently reuses a job created for different work.

### `job_attempts`

Every claim inserts a new immutable-identity attempt:

- `id`, also used as the fencing token;
- `job_id`, `workspace_id`, and monotonic `attempt_number`;
- `worker_id`;
- attempt `status`;
- `started_at`, `heartbeat_at`, `lease_expires_at`, and `finished_at`;
- bounded, redacted progress JSON;
- structured error code, class, safe message, trace ID, and retry decision;
- optional redacted result summary.

There is at most one current running attempt per job. Old attempts remain for
audit and diagnostics.

### `job_events`

`job_events` remains append-only and workspace-scoped. It gains optional
`attempt_id`, `actor_type`, and `actor_id`. Event metadata is bounded and
redacted before persistence.

Events cover enqueue, lease, heartbeat milestones, progress, success, retry,
block, unblock, dead-letter, cancel request, cancellation, expiration, manual
actions, and schedule creation.

Heartbeats are not written as one event per tick. Only lifecycle milestones and
rate-limited progress updates are appended so the audit table cannot grow at the
heartbeat frequency.

### `job_queues`

A queue row contains:

- stable `name`;
- optional `paused_at` and actor;
- global concurrency limit;
- per-workspace concurrency limit;
- default lease duration;
- timestamps and an optimistic concurrency version.

The queue row is locked only during a claim transaction. This serializes capacity
admission within one queue without holding a lock during execution. Different
queues can admit work concurrently.

### `job_queue_workspace_state`

This internal dispatch table stores `(queue_name, workspace_id,
last_claimed_at)`. It supplies a persistent round-robin cursor across worker
processes. Priority orders jobs inside one workspace; the cursor prevents a busy
workspace from starving another workspace with eligible work.

### `job_schedules`

A schedule contains:

- `id`, `workspace_id`, name, and optional description;
- target queue, handler name/version, payload, priority, and concurrency key;
- five-field cron expression and IANA timezone;
- `misfire_policy` in `skip`, `run_once`, or `catch_up`;
- bounded `max_catch_up`, required for `catch_up`;
- active or paused state;
- `next_run_at`, `last_scheduled_for`, and timestamps;
- creator and last-updating actor;
- optimistic concurrency version.

The default misfire policy is `run_once`. `skip` advances without enqueueing.
`run_once` enqueues only the most recent missed occurrence. `catch_up` enqueues
oldest-first up to `max_catch_up`, then advances past all remaining missed
occurrences.

Occurrences are computed in the declared timezone and stored as UTC instants. A
nonexistent local time during a daylight-saving jump is skipped. Repeated local
times map to two distinct UTC instants and therefore produce two occurrences.

The unique constraint `(schedule_id, scheduled_for)` prevents duplicate jobs when
scheduler replicas race or restart.

### `job_workers`

A worker presence row contains worker UUID, process identity metadata, application
version, supported queues and handler versions, start time, heartbeat time,
draining state, and shutdown timestamp. It is operational presence, not the source
of job lease truth.

Worker rows may be pruned after a configured retention period once no current
attempt references them.

## Job state machine

Canonical job statuses are:

- `queued`: waiting for `run_after` and capacity;
- `running`: owned by `current_attempt_id` until lease expiration or completion;
- `succeeded`: terminal success;
- `blocked`: paused for a recoverable external or configuration condition;
- `dead_letter`: terminal failure requiring manual inspection or retry;
- `cancelled`: terminal confirmed cancellation.

There is no separate `retry_wait` status. A retry is `queued` with a future
`run_after`, which keeps one eligibility query and preserves the existing public
contract.

Allowed transitions are:

```text
queued      -> running | cancelled
running     -> succeeded | queued | blocked | dead_letter | cancelled
blocked     -> queued | cancelled
dead_letter -> queued
```

Terminal `succeeded` and `cancelled` jobs cannot be retried. A dead-letter retry
or unblock creates a new future attempt on the same job UUID and records the
operator action.

## Claim and fencing protocol

A worker claim performs these actions in one database transaction:

1. Lock the `job_queues` row for the target queue.
2. Verify the queue is not paused and global capacity is available.
3. Select the eligible workspace with the oldest dispatch cursor while respecting
   workspace, handler, and concurrency-key capacity.
4. Select that workspace's job ordered by priority descending, `run_after`,
   creation time, and UUID, using `FOR UPDATE SKIP LOCKED`.
5. Insert `job_attempts` with a fresh UUID and lease timestamps.
6. Set the job to `running`, set `current_attempt_id`, increment
   `attempt_count`, update the workspace cursor, and append `leased`.
7. Commit before deserializing or executing the handler.

Every heartbeat and final operation uses a conditional update equivalent to:

```text
WHERE jobs.id = :job_id
  AND jobs.status = 'running'
  AND jobs.current_attempt_id = :attempt_id
```

Zero updated rows means the worker lost ownership. The worker records no canonical
success or failure and must stop any remaining cooperative work. Fencing protects
database state; it cannot reverse an external request already sent, so handler
idempotency remains mandatory.

## Handler execution contract

Handlers receive validated payload data and a `JobContext` with:

- job, attempt, workspace, and idempotency identifiers;
- cancellation status;
- rate-limited progress reporting;
- lease-health status;
- explicitly injected application resource factories.

Handlers return `None` or a JSON-serializable result of at most 64 KiB. The worker
validates and redacts the result before persistence. Larger results must be stored
by the owning subsystem and returned as an artifact reference.

Handlers classify failures using:

- `RetryableJobError`: requeue with computed backoff;
- `BlockedJobError`: move to `blocked` without consuming retry budget;
- `PermanentJobError`: move directly to `dead_letter`;
- `JobCancelled`: confirm cooperative cancellation.

An unclassified exception is retryable by default until `max_retries` is
exhausted, then becomes `dead_letter`. Its persisted error is operator-safe; the
full exception remains in structured application logs under `trace_id`.

Backoff is exponential with bounded full jitter. The handler registration defines
base and maximum delays. For retry number `n`, delay is sampled uniformly from
zero through `min(max_delay, base_delay * 2^n)`. A manual retry always grants one
new execution. It preserves `retry_count` by default, so another retryable failure
returns to `dead_letter` when the budget was already exhausted. Workspace and
global administrators may explicitly reset `retry_count` to zero after confirming
the wider retry window.

## Cancellation and shutdown

Cancelling `queued` or `blocked` work changes it immediately to `cancelled`.
Cancelling `running` work sets `cancellation_requested_at` and notifies workers.
The handler must observe cancellation through `JobContext` and raise
`JobCancelled` to confirm it.

The platform does not claim a running job was cancelled merely because a request
was made. If a handler completes before acknowledging cancellation, the job is
`succeeded` and an event records completion after the request.

On graceful shutdown a worker stops claiming, marks itself draining, continues
heartbeats, and waits up to its configured drain timeout. If the process exits or
is killed, normal lease expiration and reaping recover its work.

If a worker cannot renew a lease before a safety margin, it locally cancels the
handler task and refuses finalization. Sync thread work cannot be forcibly killed;
its context becomes fenced and any later finalization is rejected.

## Scheduler protocol

Each scheduler tick:

1. Selects due active schedules in bounded batches with `FOR UPDATE SKIP LOCKED`.
2. Computes occurrences according to timezone and misfire policy.
3. Inserts normal jobs and their enqueue events.
4. Relies on `(schedule_id, scheduled_for)` for race-safe deduplication.
5. Advances `next_run_at` in the same transaction.
6. Commits and emits a wake notification.

`run-now` creates an unscheduled job linked to the schedule for audit but does not
change `next_run_at`. Pausing prevents new occurrences and does not cancel jobs
already created. Resuming applies the schedule's configured misfire policy.

## API and authorization

### Workspace endpoints

- `GET/POST /workspaces/{workspace_id}/jobs`
- `GET /workspaces/{workspace_id}/jobs/{job_id}`
- `POST /workspaces/{workspace_id}/jobs/{job_id}/cancel`
- `POST /workspaces/{workspace_id}/jobs/{job_id}/retry`
- `POST /workspaces/{workspace_id}/jobs/{job_id}/unblock`
- `GET/POST /workspaces/{workspace_id}/job-schedules`
- `GET/PATCH/DELETE /workspaces/{workspace_id}/job-schedules/{schedule_id}`
- `POST .../{schedule_id}/pause|resume|run-now`

List endpoints use stable cursor pagination and support status, queue, handler,
schedule, and time filters. Mutations use the row version or current status as an
optimistic concurrency precondition and return `409` for stale operations.

Manual enqueue and schedule creation expose only handler registrations with
`allow_manual_enqueue=True`.

`DELETE` archives a schedule and prevents future occurrences; it does not erase
the schedule or its audit history.

### Global administrative endpoints

- `GET /admin/jobs` with workspace filters;
- `GET/PATCH /admin/job-queues/{queue_name}`;
- `GET /admin/job-workers`;
- global aggregate metrics for the console.

### RBAC

- Global administrators can inspect and operate all workspaces, queues, schedules,
  and workers.
- Workspace administrators can enqueue allowed handlers and operate jobs and
  schedules in their workspace.
- Contributors and viewers have read-only access to job metadata in their
  workspace.
- Cross-workspace access always returns the established not-found/forbidden
  behavior without leaking object existence.
- All users receive redacted payloads, results, event metadata, and safe errors.
  Secrets are never persisted, so global administration cannot reveal them.

Existing domain-specific ingestion endpoints retain their current contributor
authorization during the compatibility period. This exception does not grant a
contributor access to generic enqueue, cancellation, retry, unblock, or schedule
mutations in the Background Jobs console.

## CLI

The general command surface is:

```text
adaptive-rag jobs worker
adaptive-rag jobs enqueue|list|show|cancel|retry|unblock
adaptive-rag jobs schedules create|list|show|pause|resume|run-now
adaptive-rag jobs queues list|pause|resume|configure
adaptive-rag jobs workers list
```

Commands emit machine-readable JSON by default where the existing CLI follows
that convention. Worker options include queue filters, concurrency, drain timeout,
`--once`, and `--max-jobs` for deterministic tests.

Existing ingestion commands remain compatibility aliases until a separately
approved removal:

- `jobs enqueue-ingest-source` calls the general enqueue service;
- `jobs run-worker` calls the general worker with ingestion handlers enabled.

The compatibility `run-worker --workspace-id` option narrows claims for local and
test workflows. Production Compose uses the global worker without a workspace
filter, and the old workspace-specific environment variable is documented as
deprecated.

## Web console

Settings gains a `Background Jobs` module with four submodules:

- **Jobs:** counts, oldest eligible age, filters, paginated table, and a detail
  drawer containing attempt history, event timeline, progress, result, and redacted
  payload.
- **Schedules:** next/last occurrence, timezone, misfire policy, pause/resume,
  edit, run-now, and deletion.
- **Queues:** paused state, concurrency limits, depth, running count, and oldest
  job age.
- **Workers:** live/stale/draining state, application version, supported queues and
  handlers, heartbeat age, and running attempts.

Filters are encoded in the URL. The console polls only while visible and stops on
unmount or page hide. Mutations show confirmation for destructive or bulk actions,
retain durable context inline, and use the application toast standard for
transient success or failure.

The existing authoring ingestion panel continues to call compatibility API methods
whose implementation delegates to the general job service.

## Observability and retention

Metrics include:

- queue depth and oldest eligible age;
- enqueue-to-start and execution duration histograms;
- running and capacity counts by queue, handler, and workspace;
- retries, blocks, dead letters, cancellations, and expired leases;
- active, stale, and draining workers;
- scheduler lag and misfire counts;
- stale-fencing write rejection counts.

Logs include job ID, attempt ID, handler, queue, workspace, worker, and trace ID,
but never raw payloads or results.

Retention is configurable by terminal state and age. Pruning removes attempt and
event history only with its terminal job in one transaction. Jobs referenced by
provider usage or another audit record are retained or anonymized according to the
referencing record's policy; they are not blindly deleted.

## Security and resource limits

- Payload and result JSON have hard serialized-size limits.
- Handler-specific Pydantic validation runs before enqueue and again before
  execution.
- Unknown handlers and versions are rejected before enqueue.
- Priority, retry count, catch-up count, page size, lease duration, and progress
  frequency have hard caps.
- API error responses contain stable safe codes and trace IDs, not tracebacks.
- Queue identifiers and handler names come from registries or validated slugs.
- Workers use least-privilege database credentials sufficient for job operations,
  not schema migration.
- PostgreSQL `LISTEN/NOTIFY` is an optimization; polling remains the delivery
  guarantee.

Hard caps are:

| Value | Maximum |
|---|---:|
| Serialized payload | 256 KiB |
| Serialized result | 64 KiB |
| Progress JSON | 8 KiB |
| Event metadata JSON | 16 KiB |
| Safe error message | 4 KiB |
| API page size | 200 rows |
| Absolute priority | 1,000 |
| Automatic retries | 25 |
| Lease duration | 3,600 seconds |
| Catch-up occurrences per scheduler tick | 100 |
| Persisted progress frequency | 1 update/second/attempt |

Five-field cron syntax limits recurring schedules to minute granularity. Handler
defaults may be stricter than these platform caps.

## Migration and compatibility

The migration is additive before behavior changes:

1. Add new columns with compatible defaults and create new tables and indexes.
2. Backfill existing jobs with queue `ingestion`, handler version `1`,
   `attempt_count=attempts`, derived `retry_count`, and compatible retry limits.
3. Preserve all existing job UUIDs and event rows.
4. Add constraints only after backfill validation.
5. Route existing repository operations through the new state-transition service.
6. Move ingestion handlers to the registry and general worker.
7. Add API/CLI/console surfaces.
8. Remove the old long-transaction execution path only after compatibility tests
   pass.

Compatibility responses project `locked_by` and `locked_until` from the current
attempt, and project `attempts`/`max_attempts` from the new counters. Existing safe
ingestion payloads remain visible exactly as before.

Application startup fails closed when its code requires a newer queue schema. A
database migration does not silently reinterpret open jobs. Open jobs with an
unsupported handler version remain queued and surface as unroutable in metrics and
the console.

Rollback means rolling application code back while retaining additive tables and
columns. Once jobs have been executed with the new attempt model, destructive
schema rollback is not supported; forward repair preserves audit history.

## Verification strategy

Development follows test-driven development: each transition, API behavior, and
UI action begins with a failing test and is implemented minimally before
refactoring.

### Unit tests

- transition matrix and fencing preconditions;
- retry budget, exponential backoff, and bounded jitter;
- handler registration, payload/result limits, and redaction;
- cron parsing, timezone/DST behavior, and all misfire policies;
- cancellation and manual retry semantics;
- API schemas and cursor encoding.

### PostgreSQL integration tests

- clean Alembic upgrade and existing-data backfill;
- transaction rollback prevents enqueue visibility;
- concurrent identical enqueue returns one open job;
- multiple workers never claim the same attempt;
- queue, workspace, handler, and concurrency-key limits hold under races;
- persistent round-robin prevents workspace starvation;
- scheduler replicas create one job per occurrence;
- stale heartbeat, completion, failure, and progress writes update zero rows;
- reaper produces exactly one recovery transition.

These tests use the repository's Testcontainers PostgreSQL infrastructure, not
SQLite substitutes.

### Fault-injection tests

- kill a worker during a handler and recover after lease expiry;
- pause or break heartbeat renewal and reject obsolete finalization;
- lose notifications and recover by polling;
- stop scheduler replicas between job insert and the next tick;
- terminate during graceful drain and verify remaining work is recoverable.

### API, CLI, and frontend tests

- RBAC for global admin, workspace admin, contributor, and viewer;
- cross-workspace isolation and payload/error redaction;
- cursor pagination and filters;
- enqueue, cancel, retry, unblock, schedule, queue, and worker operations;
- compatibility ingestion routes and commands;
- console loading, empty, error, stale mutation, polling cleanup, and responsive
  states.

### End-to-end acceptance

The delivery gate runs Docker Compose with PostgreSQL, API, scheduler, and at least
two workers. It processes 500 jobs across four workspaces and proves:

- no lost job and no duplicate canonical finalization;
- no workspace starvation;
- configured concurrency limits are never exceeded;
- a killed worker's job is recovered;
- a rolled-back enqueue is never observed;
- a cron occurrence is created once;
- current ingestion flows and the v1 quality gate remain green.

Latency and throughput are recorded as benchmark evidence but do not use fragile
wall-clock CI thresholds. Correctness, bounded connections, short transactions,
and absence of lock growth are hard gates.

## Rejected alternatives

### Full PgQueuer replacement

Rejected because its active/log schema and status model would require replacing or
mirroring the public Adaptive RAG job model. Workspace RBAC, blocking, UUID
references, audit events, and compatibility surfaces would remain application
work, while async-only execution would increase migration scope.

### Procrastinate replacement

Rejected for the same domain mismatch and because force-killed worker recovery
requires application-supplied periodic recovery logic. Its SQLAlchemy connector
supports enqueue but not worker execution.

### Library transport plus domain projection

Rejected because two mutable state machines would require reconciliation. The
design requires one canonical state and transactional transitions.

## Completion criteria

The job platform is complete when:

- all goals and compatibility guarantees above are implemented;
- all verification layers pass against real PostgreSQL;
- the Docker Compose acceptance scenario passes with fault injection;
- no handler runs in a claim transaction;
- obsolete attempts cannot mutate canonical state;
- API, CLI, and console expose safe, authorized operations;
- queue and scheduler runbooks document deployment, migration, recovery, metrics,
  retention, and rollback behavior.
