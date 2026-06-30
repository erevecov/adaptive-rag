# Runtime acceptance

Este runbook valida el flujo end-to-end despues de Runtime settings. Complementa
`docs/v1-quality-gate.md`: en vez de inyectar providers desde el CLI, configura
provider connections, model catalog, slots globales y overrides por proyecto en
la base local, y despues ejecuta ingestion, indexing y chat citado con esa
resolucion efectiva.

El camino default usa providers `fake`. No llama Qwen hosted, no requiere
credenciales y no consume red ni presupuesto externo.

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

Para guardar API keys de providers desde Runtime settings, el backend necesita
una Fernet key estable. En local, si `ADAPTIVE_RAG_PROVIDER_SECRETS_KEY` no esta
configurada, la API crea y reutiliza `.adaptive-rag/provider-secrets.key` de
forma automatica. Ese directorio esta ignorado por Git; preservalo si quieres
seguir descifrando secretos guardados entre reinicios. En produccion, configura
`ADAPTIVE_RAG_PROVIDER_SECRETS_KEY` explicitamente.

## Ejecutar acceptance

Ejecuta el smoke post-runtime-settings:

```bash
uv run adaptive-rag acceptance runtime-settings-smoke
```

Para guardar evidencia local:

```bash
mkdir -p artifacts
uv run adaptive-rag acceptance runtime-settings-smoke \
  --output artifacts/runtime-acceptance.json
```

El comando crea una provider connection fake global, sincroniza el model
catalog fake, configura defaults globales para `chat`, `dense_embedding` y
`contextualization`, crea un override de proyecto para `dense_embedding`, ingiere
contenido Markdown, indexa chunks y ejecuta chat con citations usando providers
resueltos desde runtime settings persistidos.

La salida esperada tiene esta forma:

```json
{
  "status": "succeeded",
  "criteria": [
    {"id": "model_catalog_synced", "status": "passed"},
    {"id": "global_runtime_defaults", "status": "passed"},
    {"id": "project_runtime_override", "status": "passed"},
    {"id": "effective_runtime_resolution", "status": "passed"},
    {"id": "cited_chat", "status": "passed"},
    {"id": "secret_values_not_exposed", "status": "passed"}
  ],
  "runtime_settings": {
    "global_connection": {"provider": "fake", "connection_type": "fake"},
    "model_catalog": {
      "synced_count": 5,
      "model_ids": [
        "retrieval-grounded-local-v1",
        "fake-embedding-v1",
        "deterministic-context-v1"
      ]
    },
    "effective_project_settings": {
      "chat": {"source": "inherited"},
      "dense_embedding": {"source": "overridden"}
    }
  },
  "first_run": {
    "status": "succeeded",
    "job": {"status": "succeeded"},
    "chunk_count": 2,
    "citation_count": 1
  },
  "opt_in_systems": ["hosted_qwen", "local_openai_compatible_live"]
}
```

## Datos propios

Puedes reemplazar el sample por contenido propio:

```bash
uv run adaptive-rag acceptance runtime-settings-smoke \
  --project-name "Runtime acceptance corpus" \
  --source-external-id "notes.md" \
  --content "# Notes

Runtime settings evidence lives here." \
  --question "What runtime evidence is in my notes?"
```

## Opt-in fuera del gate default

- Qwen hosted: opcional, requiere `ADAPTIVE_RAG_QWEN_API_KEY`, base URL y puede
  consumir presupuesto.
- Providers locales OpenAI-compatible: opcionales, requieren endpoint local
  levantado y model IDs disponibles en el model catalog.
- Rerank hosted y Neo4j/graph siguen opt-in y no cambian el default.

## Qwen hosted production defaults

Qwen no se activa al arrancar la API ni el CLI. El flujo production-ready es
conectar el provider desde Runtime settings y sincronizar su model catalog. No
hace falta un comando adicional de bootstrap: despues de un sync exitoso de una
connection Qwen, el backend materializa defaults faltantes desde modelos
conocidos del catalogo.

En una instalacion limpia, el sync configura:

- pool global de chat con `qwen-plus` como default si el pool esta vacio;
- `dense_embedding` con `text-embedding-v4` si el slot no tiene default;
- `rerank` con `qwen3-rerank` si el slot no tiene default;
- `sparse_embedding` con `text-embedding-v4` solo si la connection usa
  DashScope native TextEmbedding, no una base OpenAI-compatible.

El sync no pisa defaults que el usuario ya eligio y no guarda API keys desde
environment. Para llamadas live, incluye el API key al guardar la provider
connection en Runtime settings o deja disponible `ADAPTIVE_RAG_QWEN_API_KEY`
en el runtime.

## Troubleshooting

- Si `uv run alembic upgrade head` falla, confirma que Postgres esta arriba y
  que `ADAPTIVE_RAG_DATABASE_URL` apunta a `localhost:5432`.
- Si guardar el API key de una provider connection falla, confirma que
  `ADAPTIVE_RAG_PROVIDER_SECRETS_KEY` contiene una Fernet key valida o que el
  proceso puede crear y leer `ADAPTIVE_RAG_PROVIDER_SECRETS_KEY_FILE`.
- Si el smoke falla con `runtime acceptance model catalog is empty`, revisa la
  provider connection configurada por el comando o vuelve a ejecutar sobre una
  base limpia.
- Si el smoke falla con `runtime acceptance chat returned no citations`, usa
  contenido mas explicito o confirma que el proyecto tenga chunks con
  embeddings.
