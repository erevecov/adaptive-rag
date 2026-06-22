# Adaptive RAG

Sistema RAG personal, aislado por proyecto, pensado para aprendizaje y
portafolio.

## Alcance v1.0

La release v1.0 es local-first y conservadora: dense retrieval con pgvector,
chat con citations, rerank opt-in, evals offline, observability local y un
paquete Docker Compose para API, worker project-scoped y Postgres/pgvector.

No requiere Qwen hosted, Neo4j, voice, MCP server, auth multi-user ni
observability hosted para el gate default. Qwen, rerank hosted y Neo4j quedan
como smokes opt-in con presupuesto/configuración explícita.

## Desarrollo local

```bash
uv sync --extra dev
uv run alembic upgrade head
uv run pytest
uv run ruff check .
uv run mypy src
```

Smokes CLI sin servicios hosted. Los comandos de evals requieren una base local
inicializada; se pueden ejecutar dentro de Docker Compose como se muestra abajo.

```bash
uv run adaptive-rag version
uv run adaptive-rag health
```

## Stack local de release

El paquete local usa Postgres con pgvector y la API FastAPI:

```bash
docker compose up --build postgres api
docker compose run --rm api alembic upgrade head
curl http://localhost:8000/health
```

El worker procesa jobs `ingest_source` por proyecto:

```bash
uv run adaptive-rag jobs run-worker --project-id <project-id> --once
```

En Docker Compose el worker usa profile porque requiere `project_id`:

```bash
ADAPTIVE_RAG_WORKER_PROJECT_ID=<project-id> docker compose --profile worker up worker
```

Detalles y runbook: `docs/architecture/v1-release-package.md`.

## Demo de portafolio

El demo reproducible usa fixtures offline y providers `fake`; no consume
credenciales ni costo externo:

```bash
mkdir -p artifacts
docker compose run --rm api adaptive-rag evals run evals/fixtures/retrieval-smoke.json \
  --mode offline \
  --output artifacts/v1-retrieval-smoke.json
docker compose run --rm api adaptive-rag evals run evals/fixtures/chat-smoke.json \
  --mode offline \
  --output artifacts/v1-chat-smoke.json
```

Los artefactos en `artifacts/` son locales y se pueden regenerar cuando se
necesite evidencia fresca.

## Smoke Neo4j opt-in

Neo4j no forma parte del stack obligatorio. Para validar un entorno live local o
managed, configura `graph_store=neo4j` por variables `ADAPTIVE_RAG_*` y ejecuta
el smoke de conectividad:

```bash
uv run adaptive-rag graph neo4j-smoke
```

Ruta local esperada: Neo4j Desktop o Docker exponiendo Bolt en `7687`, por
ejemplo `ADAPTIVE_RAG_NEO4J_URI=neo4j://localhost:7687`.

Ruta managed esperada: URI cifrada tipo `neo4j+s://...` con username/password
desde env. El smoke serializa solo scheme/clasificacion de URI, status y error
code; no imprime host completo ni password.

## Backfill/reindex Neo4j opt-in

Con `graph_store=neo4j` configurado, la proyeccion graph derivada se reconstruye
por proyecto:

```bash
uv run adaptive-rag graph backfill <project-id> --source-watermark chunks:v1
uv run adaptive-rag graph reindex <project-id> --source-watermark chunks:v2
```

Los comandos imprimen un reporte JSON con status, duracion, conteos y error
code. Salen con codigo `0` solo cuando la proyeccion termina en `ready`.

## Retrieval graph smoke opt-in

Con una proyeccion `ready`, se puede validar la ruta live de lectura graph:

```bash
uv run adaptive-rag graph retrieval-smoke <project-id> --query "alpha question" --limit 5
```

El comando imprime status, latencia, conteos, `fallback_reason`, chunk ids y
sources. Sale con codigo `0` solo si obtiene resultados `strategy=graph`; si
cae a dense fallback o no hay hits graph, sale con codigo `1`.

## Evidencia graph live

Para consolidar la evidencia M19, ejecuta el quality gate dense-vs-graph junto
con los artefactos JSON emitidos por backfill/reindex y retrieval smoke:

```bash
uv run adaptive-rag evals graph-live-evidence <suite.json> \
  --operation-report backfill.json \
  --operation-report reindex.json \
  --retrieval-smoke-report retrieval-smoke.json \
  --graph-operational-cost-usd 12.50 \
  --graph-operational-cost-notes "Neo4j Aura daily estimate"
```

El comando reporta `comparison_metrics`, `operational_metrics`, `error_codes`,
`graph_operational_cost`, `operation_reports` y `retrieval_smoke_reports`.
Sale con codigo `0` solo cuando el quality gate pasa y todos los artefactos
live quedan `ready`; no ejecuta operaciones Neo4j por si mismo.

## Documentación

La documentación del repositorio se escribe en español. Se mantienen en inglés
los nombres de comandos, APIs, paquetes y términos técnicos cuando eso evita
ambigüedad.
