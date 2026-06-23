# V1 quality gate

Este runbook genera la evidencia final de producto para v1.0. Parte del mismo
camino local-first de `docs/first-run.md`, pero agrega una decision explicita
de release y criterios machine-readable.

El gate default usa providers `fake`, Postgres/pgvector local y dense retrieval.
Qwen, rerank hosted y Neo4j son opt-in; no son requisito para que el gate local
sea valido.

## Requisitos

- Python 3.12+.
- Docker con Compose para Postgres/pgvector.
- `uv`.

## Setup

Instala dependencias de desarrollo:

```bash
uv sync --extra dev
```

Arranca Postgres local:

```bash
docker compose up --build postgres
```

En otra terminal, aplica migraciones:

```bash
uv run alembic upgrade head
```

## Ejecutar el gate

Ejecuta el gate final de producto:

```bash
uv run adaptive-rag v1 quality-gate
```

Para guardar evidencia local:

```bash
mkdir -p artifacts
uv run adaptive-rag v1 quality-gate --output artifacts/v1-quality-gate.json
```

El comando crea un project/source, procesa ingestion, chunks y embeddings,
ejecuta chat con citations y evalua criterios de release sobre ese reporte.
La salida esperada tiene esta forma:

```json
{
  "status": "succeeded",
  "release_decision": "ready_for_v1_0",
  "criteria": [
    {"id": "public_product_flow", "status": "passed"},
    {"id": "ingestion_job_state", "status": "passed"},
    {"id": "indexed_evidence", "status": "passed"},
    {"id": "cited_chat", "status": "passed"},
    {"id": "public_follow_up_commands", "status": "passed"},
    {"id": "opt_in_boundaries", "status": "passed"}
  ],
  "first_run": {
    "status": "succeeded",
    "job": {"status": "succeeded"},
    "chunk_count": 2,
    "embedded_chunk_count": 2,
    "citation_count": 1
  },
  "deferred_defaults": [
    "hosted_qwen",
    "hosted_rerank",
    "neo4j_graph",
    "auth_multi_user",
    "pdf_office_ingestion",
    "voice",
    "mcp_server",
    "hosted_observability"
  ],
  "manual_release_notes": "ready_for_v1_0 means the local product gate evidence passed; a manual git tag or GitHub release remains a separate human action."
}
```

`ready_for_v1_0` significa que el producto local-first cumple el gate final en
este checkout. Un manual git tag or GitHub release sigue siendo una accion
humana separada y no la ejecuta el comando.

## Datos propios

Puedes reemplazar el sample por contenido propio:

```bash
uv run adaptive-rag v1 quality-gate \
  --project-name "My v1 corpus" \
  --source-external-id "notes.md" \
  --content "# Notes

My release evidence lives here." \
  --question "What release evidence is in my notes?"
```

## Opt-in fuera del gate default

- Qwen hosted: opcional, requiere credenciales y puede consumir presupuesto.
- Rerank hosted: opcional y medible, no cambia el default dense.
- Neo4j/graph: opcional y en `hold_default`, no reemplaza Postgres/pgvector.
- Auth multi-user, PDF/Office, voice, MCP server y hosted observability siguen
  deferidos salvo nuevo OpenSpec.

## Troubleshooting

- Si `uv run alembic upgrade head` falla, confirma que Postgres esta arriba y
  que `ADAPTIVE_RAG_DATABASE_URL` apunta a `localhost:5432`.
- Si el gate falla con `first-run ingestion did not process`, inspecciona el
  job con `adaptive-rag jobs show`.
- Si el gate falla con `first-run chat returned no citations`, usa contenido
  mas explicito o confirma que el proyecto tenga chunks con embeddings.
