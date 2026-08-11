# job-queue Specification

## Purpose

Definir la plataforma PostgreSQL general para cualquier trabajo en segundo
plano: handlers tipados/versionados, jobs de workspace o sistema, ejecución
at-least-once con fencing, schedules durables y control operativo completo.

## Requirements

### Requirement: Registered handlers define the executable contract

The system MUST enqueue and execute only statically registered handler name and
version pairs. The registry MUST define typed payload validation, queue, scope,
retry/lease policy, concurrency policy and redaction.

#### Scenario: Unknown or invalid work is rejected before persistence

- **WHEN** a caller enqueues an unknown handler/version or invalid payload
- **THEN** no job is inserted
- **AND** payload/result sizes and secret-like material are rejected or redacted

### Requirement: Jobs support workspace and system scopes

The system MUST persist jobs with exactly one valid scope: workspace jobs have
`workspace_id`; system jobs do not. Jobs MUST include queue, immutable handler
version, priority, run time, retry policy, idempotency/fingerprint, state,
version and the current attempt fence.

#### Scenario: Transactional enqueue is idempotent

- **WHEN** equivalent work is enqueued twice with the same scope and
  idempotency key
- **THEN** both calls identify one durable job
- **AND** reuse with a different canonical fingerprint is rejected
- **AND** the insert and PostgreSQL notification become visible only on commit

#### Scenario: State and scope invariants are database enforced

- **WHEN** a row violates the allowed states, scope relation, bounded fields or
  attempt fence relation
- **THEN** PostgreSQL rejects the mutation

### Requirement: Claims are fair and capacity constrained

Workers MUST claim eligible jobs through short PostgreSQL transactions using
row locks with `SKIP LOCKED`. Selection MUST honor queue pause, priority,
`run_after`, fair workspace rotation and limits at queue, workspace, handler and
concurrency-key levels.

#### Scenario: Replicated workers claim without duplication or starvation

- **WHEN** concurrent compatible workers drain jobs from multiple workspaces
- **THEN** one current attempt owns each running job
- **AND** configured shared limits are never exceeded
- **AND** every non-empty eligible workspace receives claims

### Requirement: Attempts use leases, heartbeats and fencing

The system MUST persist every attempt separately. Heartbeat, progress and final
state writes MUST require the job's current `attempt_id`.

#### Scenario: A crashed worker is recovered safely

- **WHEN** a current lease expires after worker loss
- **THEN** a replicated reaper expires that attempt exactly once
- **AND** requeues or dead-letters according to retry budget
- **AND** a later attempt may finish the job
- **AND** any write from the old attempt is rejected and audited as
  `fenced_write_rejected`

### Requirement: Lifecycle operations are explicit and audited

The system MUST support succeeded, retryable failure with full-jitter backoff,
blocked, dead-letter, cooperative cancellation, retry and unblock transitions.
Every control and execution transition MUST append a redacted event.

#### Scenario: Running cancellation is cooperative

- **WHEN** an operator cancels a running job
- **THEN** the cancellation request is persisted and visible to its handler
- **AND** handler confirmation ends it as cancelled
- **AND** a completion that wins the race remains succeeded and is audited

#### Scenario: Optimistic control mutation conflicts

- **WHEN** an API, CLI or console mutation uses a stale job/queue/schedule
  version
- **THEN** it fails without overwriting the newer state

### Requirement: Worker wake-up is durable without notifications

Workers MUST combine PostgreSQL `LISTEN/NOTIFY` with bounded polling. Local
concurrency MUST be configurable and advertised; shutdown MUST advertise
draining and use a bounded drain timeout.

#### Scenario: Notifications are unavailable

- **WHEN** an insert notification is lost or its trigger is disabled
- **THEN** an eligible job is still claimed through polling

### Requirement: Cron schedules are durable and replica safe

The system MUST persist schedules with registered handler/version, scope,
payload, cron expression, IANA timezone, misfire policy, occurrence cursor and
optimistic version. Replicated schedulers MUST materialize each occurrence at
most once.

#### Scenario: DST and misfires are deterministic

- **WHEN** a timezone crosses an ambiguous/non-existent local time or the
  scheduler resumes late
- **THEN** the next occurrence is computed deterministically
- **AND** `skip`, `run_once` or bounded `catch_up` is applied as configured

### Requirement: API, CLI and console expose scoped operations

Workspace readers MUST list/detail jobs and schedules only in their workspace;
workspace admins MUST perform allowed mutations/manual enqueue. Superadmins
MUST exclusively control system jobs, queues, workers and global metrics.

#### Scenario: Direct unauthorized console navigation

- **WHEN** a non-superadmin navigates directly to Queues or Workers
- **THEN** the UI returns to an allowed Background Jobs view
- **AND** makes no global admin request

### Requirement: Operational metrics and retention are bounded

Metrics MUST expose queue depth/age/capacity, running work, timing samples,
outcomes, expired leases/fencing, worker states, unroutable work and scheduler
lag/misfires through bounded result sets. Retention MUST preview or delete only
bounded batches of old terminal jobs not protected by provider-usage/audit
references.

#### Scenario: Retention dry-run and apply

- **WHEN** retention runs without `--apply`
- **THEN** it returns candidate IDs/counts without mutation
- **WHEN** the same eligible batch runs with `--apply`
- **THEN** jobs and cascading attempts/events delete in one transaction
- **AND** non-terminal, recent and protected jobs remain

### Requirement: Ingestion compatibility uses the general platform

`ingest_source`, `index_document_version` and provider pricing sync MUST be
registered handlers executed by the general worker/scheduler. Legacy public
commands and ingestion operations MUST remain compatibility adapters.

#### Scenario: Ingestion enqueues indexing

- **WHEN** `ingest_source` succeeds for a valid source
- **THEN** it creates/reuses its document version
- **AND** transactionally enqueues `index_document_version`
- **AND** both jobs are visible through the general job detail/events contract
