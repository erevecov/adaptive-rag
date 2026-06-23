# First run local

Este runbook lleva una instalacion local desde cero hasta una respuesta de chat
con citations usando datos sample creados por superficies publicas. El camino
default usa providers `fake`; Qwen, rerank hosted y Neo4j son opt-in y no se
requieren para validar el flujo local.

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

## Smoke de producto

Ejecuta el camino completo authoring -> ingestion -> indexing -> cited chat:

```bash
uv run adaptive-rag first-run smoke
```

El comando crea un project, crea una source Markdown, encola y procesa un job
`ingest_source`, crea chunks, persiste embeddings densos fake y pregunta al
chat local. La salida es JSON machine-readable. Campos esperados:

```json
{
  "status": "succeeded",
  "project": {"id": "...", "name": "Adaptive RAG First Run"},
  "source": {"id": "...", "external_id": "first-run.md"},
  "job": {"id": "...", "status": "succeeded"},
  "document_version_id": "...",
  "chunk_count": 2,
  "embedded_chunk_count": 2,
  "citation_count": 1,
  "answer": "..."
}
```

Para usar contenido propio sin fixtures internas:

```bash
uv run adaptive-rag first-run smoke \
  --project-name "My local corpus" \
  --source-external-id "notes.md" \
  --content "# Notes

My local evidence lives here." \
  --question "What evidence is in my notes?"
```

## Siguientes comandos

El reporte incluye `next_commands`. Tambien puedes inspeccionar manualmente:

```bash
uv run adaptive-rag sources list --project-id <project-id>
uv run adaptive-rag jobs list --project-id <project-id>
uv run adaptive-rag chat ask --project-id <project-id> --message "What did I ingest?"
```

## Opt-in

Qwen hosted, rerank hosted y Neo4j no forman parte del default first run. Para
probarlos, configura las variables `ADAPTIVE_RAG_*` relevantes en `.env` y usa
los smokes especificos documentados en `README.md`. Esas rutas pueden consumir
red, credenciales o presupuesto; el smoke default de este runbook no.

## Troubleshooting

- Si `uv run alembic upgrade head` falla, confirma que Postgres esta arriba y
  que `ADAPTIVE_RAG_DATABASE_URL` apunta a `localhost:5432`.
- Si el smoke falla con `first-run ingestion did not process`, revisa el campo
  `last_error` del job con `adaptive-rag jobs show`.
- Si el smoke falla con `first-run chat returned no citations`, ejecuta otra
  vez con contenido mas explicito o revisa que el proyecto tenga chunks con
  embeddings.
