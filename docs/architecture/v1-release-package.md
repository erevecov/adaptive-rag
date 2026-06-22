# V1 release package

Estado: listo para M21.

## Stack local default

El paquete v1.0 es local-first y no requiere Qwen hosted, Neo4j, voz,
observability SaaS ni servicios externos para el gate offline.

Servicios:

- `postgres`: Postgres 16 con pgvector.
- `api`: FastAPI en `http://localhost:8000`.
- `worker`: Typer CLI `adaptive-rag jobs run-worker`, habilitado por profile
  porque el worker actual es project-scoped y requiere `project_id`.

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

## Worker

El worker procesa jobs `ingest_source` de un proyecto usando Postgres como
queue. Para una corrida de smoke de un solo job:

```bash
uv run adaptive-rag jobs run-worker \
  --project-id <project-id> \
  --worker-id local-smoke \
  --once
```

Para levantarlo dentro de Docker Compose:

```bash
ADAPTIVE_RAG_WORKER_PROJECT_ID=<project-id> docker compose --profile worker up worker
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
