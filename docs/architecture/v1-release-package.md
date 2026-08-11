# V1 release package

Estado: plataforma PostgreSQL general de jobs incorporada al paquete v1.

## Stack local default

El paquete v1.0 es local-first y no requiere Qwen hosted, Neo4j, voz,
observability SaaS ni servicios externos para el gate offline.

Servicios:

- `postgres`: Postgres 16 con pgvector.
- `api`: FastAPI en `http://localhost:8000`.
- `worker`: proceso general `adaptive-rag jobs worker`, habilitado por profile;
  consume colas de workspace y sistema sin scope fijo.
- `scheduler`: cron durable replicable `adaptive-rag jobs scheduler`.
- `frontend`: consola operativa de Jobs/Schedules y, para superadmins,
  Queues/Workers.

## Arranque

```bash
cp .env.example .env
docker compose up --build postgres api
```

La API expone health check:

```bash
curl http://localhost:8000/health
```

Las migraciones se ejecutan de forma explicita:

```bash
docker compose run --rm api alembic upgrade head
```

## Worker y scheduler

PostgreSQL es broker y fuente de verdad. Para una corrida de smoke de un solo
job o un proceso concurrente:

```bash
uv run adaptive-rag jobs worker --once
uv run adaptive-rag jobs worker \
  --queues ingestion,default,system --concurrency 8
uv run adaptive-rag jobs scheduler --once
```

Para levantarlo dentro de Docker Compose:

```bash
docker compose --profile worker up worker
docker compose up scheduler
```

El despliegue aplica Alembic antes de iniciar procesos. Workers usan leases,
heartbeats y fencing; el reaper recupera intentos vencidos. `LISTEN/NOTIFY`
acelera el wake-up y polling garantiza progreso cuando faltan notificaciones.
La cola soporta límites globales/por workspace/handler/clave, retries con
jitter, blocked/dead-letter, cancelación cooperativa e idempotencia.

Los schedules usan cron + timezone IANA con políticas `skip`, `run_once` y
`catch_up`. La consola y API mantienen separación RBAC entre scope workspace y
controles globales de superadmin.

Runbook canónico con rol DB mínimo, pausas, diagnóstico, métricas, retención y
rollback: `docs/architecture/job-platform-runbook.md`.

## Evidencia de aceptación de jobs

La suite PostgreSQL ejecuta 500 jobs en cuatro workspaces con cuatro workers de
ocho slots, verifica límites compartidos, ausencia de pérdida/finalización
duplicada y conexiones acotadas. Las pruebas de fault injection matan un worker
real, recuperan el lease, rechazan la escritura obsoleta, prueban polling sin
NOTIFY y ejecutan el ciclo con un rol sin DDL/Alembic.

```bash
uv run pytest tests/integration/jobs/test_acceptance_pg.py \
  tests/integration/jobs/test_fault_recovery_pg.py \
  tests/integration/jobs/test_retention_pg.py -q -s
```

## Demo offline

El demo de portafolio usa fixtures deterministicas y providers `fake`. Requiere
Postgres/pgvector local inicializado, pero no credenciales hosted:

```bash
docker compose run --rm api adaptive-rag evals run evals/fixtures/retrieval-smoke.json --mode offline
docker compose run --rm api adaptive-rag evals run evals/fixtures/chat-smoke.json --mode offline
```

Para generar artefactos JSON locales:

```bash
mkdir -p artifacts
docker compose run --rm api adaptive-rag evals run evals/fixtures/retrieval-smoke.json \
  --mode offline \
  --output artifacts/v1-retrieval-smoke.json
docker compose run --rm api adaptive-rag evals run evals/fixtures/chat-smoke.json \
  --mode offline \
  --output artifacts/v1-chat-smoke.json
```

`artifacts/` no es parte del contrato del repo; los comandos son reproducibles
y se pueden ejecutar en CI o localmente cuando se necesite evidencia fresca.

## Hosted opt-in

Los smokes hosted de Qwen, rerank o Neo4j son opcionales. Deben ejecutarse con
presupuesto explicito (`--max-cost-usd` cuando aplique) y no bloquean el gate
offline de release.
