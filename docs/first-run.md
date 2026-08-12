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

Arranca Postgres local (o el stack all-in-one con API/frontend):

```bash
docker compose up --build postgres
# Demo UI (opcional):
# docker compose up --build postgres api frontend
```

En otra terminal, aplica migraciones **antes** de first-run o de usar la API:

```bash
uv run alembic upgrade head
# con stack compose:
# docker compose exec api uv run alembic upgrade head
```

### Primer usuario para la UI

El smoke CLI de la siguiente seccion no necesita login. Para usar la UI, copia
`.env.example` a `.env`, configura un valor aleatorio y temporal para
`ADAPTIVE_RAG_BOOTSTRAP_SECRET`, levanta `postgres migrate api frontend` y crea
el primer superadmin:

```bash
export ADAPTIVE_RAG_BOOTSTRAP_SECRET='pega-aqui-el-mismo-valor-de-dotenv'
curl --fail-with-body http://localhost:8000/auth/setup \
  -H 'Content-Type: application/json' \
  -H "X-Setup-Secret: $ADAPTIVE_RAG_BOOTSTRAP_SECRET" \
  -d '{"email":"admin@example.com","display_name":"Local Admin","password":"change-this-strong-password"}'
```

El header debe coincidir con el secreto cargado por la API. El setup es de un
solo uso y falla cerrado si ya existe cualquier usuario. Borra el secreto y
reinicia la API despues; inicia sesion en `http://localhost:5173` con el email y
password anteriores.

Desde `Settings > Authoring`, un superadmin puede crear identidades globales y
copiar la password temporal mostrada una sola vez. Un admin de workspace puede
agregar una identidad ya existente por email y asignarle un rol solo en ese
workspace.

## Smoke de producto

Ejecuta el camino completo authoring -> ingestion -> indexing -> cited chat:

```bash
uv run adaptive-rag first-run smoke
```

El comando crea un workspace, crea una source Markdown, encola y procesa un job
`ingest_source`, crea chunks, genera `contextual_summary`, persiste embeddings
densos fake y pregunta al chat local. La salida es JSON machine-readable.
Campos esperados:

```json
{
  "status": "succeeded",
  "workspace": {"id": "...", "name": "Adaptive RAG First Run"},
  "source": {"id": "...", "external_id": "first-run.md"},
  "job": {"id": "...", "status": "succeeded"},
  "document_version_id": "...",
  "chunk_count": 2,
  "contextualized_chunk_count": 2,
  "reused_contextualized_chunk_count": 0,
  "embedded_chunk_count": 2,
  "citation_count": 1,
  "answer": "..."
}
```

Para usar contenido propio sin fixtures internas:

```bash
uv run adaptive-rag first-run smoke \
  --workspace-name "My local corpus" \
  --source-external-id "notes.md" \
  --content "# Notes

My local evidence lives here." \
  --question "What evidence is in my notes?"
```

## Siguientes comandos

El reporte incluye `next_commands`. Tambien puedes inspeccionar manualmente:

```bash
uv run adaptive-rag sources list --workspace-id <workspace-id>
uv run adaptive-rag jobs list --workspace-id <workspace-id>
uv run adaptive-rag chat ask --workspace-id <workspace-id> --message "What did I ingest?"
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
  vez con contenido mas explicito o revisa que el workspace tenga chunks con
  embeddings.
