# Diseno M4 de superficie de retrieval

## Contexto

M3 dejo un vertical slice persistente completo: ingestion crea
`document_versions`, chunking preserva offsets, embeddings persisten vectores
densos y `DenseRetriever` rankea chunks con filtros antes de ordenar. M4 debe
convertir ese baseline en una superficie de uso minimo, sin mezclar todavia
chat/tool calling ni retrieval hibrido.

## Enfoques considerados

### A. Empezar por chat/tool calling

Chat es visible y se alinea con la vision v1, pero exige orquestacion,
persistencia de sesiones, tool calls, provider runtime, prompts y reglas de
retrieval-first. No es recomendable como primer paso post-M3 porque ocultaria
errores de retrieval detras de comportamiento del modelo.

### B. Superficie minima de retrieval API/CLI

Exponer retrieval primero permite validar filtros, citations, serialization,
errores y contratos de usuario sobre el baseline M3. Es la opcion recomendada
porque produce un punto de integracion claro para chat posterior y mantiene los
tests deterministas con providers fake.

### C. Retrieval hibrido antes de API/CLI

Agregar lexical, RRF, sparse o rerank antes de una superficie estable mejora el
ranking potencial, pero aumenta la matriz de errores sin haber fijado todavia
el contrato externo. No es recomendable para M4 inicial.

## Decision

Usar el enfoque B: una superficie minima de retrieval API/CLI sobre dense
retrieval exacto.

## Secuencia de M4

### 1. `m4-retrieval-service-contract`

Crear una capa pequena que recibe query text, genera query embedding mediante un
provider inyectado y llama a `DenseRetriever`.

Alcance:

- Request/response dataclasses o schemas internos para retrieval.
- Reuso de `DenseEmbeddingProvider` o protocolo equivalente para query
  embeddings.
- Provider fake determinista en tests.
- Mapeo de filtros externos a `DenseRetrievalFilters`.
- Errores estables para query vacia, limite invalido, filtros invalidos y
  dimension incorrecta.

Fuera de alcance:

- Qwen live obligatorio.
- Lexical retrieval, sparse retrieval, RRF y rerank.
- Chat/tool calling.
- Persistencia de `retrieval_runs`.

### 2. `m4-retrieval-api-endpoint`

Agregar el endpoint minimo `POST /projects/{project_id}/retrieval/search`.

Alcance:

- Request JSON con `query`, `limit` y `metadata_filter`.
- Response JSON con results, scores y citations.
- Rechazo de campos de filtro desconocidos.
- Tests de API con dependency overrides/fakes.

Fuera de alcance:

- Auth/API keys.
- Streaming.
- Chat endpoints.
- Creacion de sources o ingestion jobs via API.

### 3. `m4-retrieval-cli-command`

Agregar `adaptive-rag retrieval search` sobre el mismo servicio.

Alcance:

- Flags de proyecto, query, limit y filtros tipados.
- Salida JSON por defecto o flag de formato estable para tests.
- Manejo de errores consistente con la API.

Fuera de alcance:

- CLI interactiva.
- Worker runner.
- Chat CLI.
- Eval CLI.

### 4. `m4-quality-gate`

Cerrar M4 cuando los slices anteriores esten mergeados, validando tests, lint,
types, specs y docs, y archivando el change.

## Riesgos y mitigaciones

- Riesgo: endpoint requiere providers live para tests.
  Mitigacion: provider fake/inyeccion obligatoria en el contrato del servicio.
- Riesgo: API y CLI divergen en filtros o formato.
  Mitigacion: ambos llaman al mismo servicio y comparten schemas/mappers.
- Riesgo: chat se acopla prematuramente al endpoint.
  Mitigacion: chat queda fuera de M4 inicial; su futuro change consume el
  servicio ya estabilizado.
- Riesgo: se expone query embedding como detalle publico.
  Mitigacion: la superficie publica recibe query text; embeddings quedan como
  detalle interno testeado con fakes.

## Validacion esperada por slice

Cada slice debe ejecutar:

```text
uv run pytest
uv run ruff check .
uv run mypy src
openspec validate <change-id> --strict
openspec validate --specs --strict
```

Los slices de API/CLI deben incluir tests de error y serialization, ademas de
paridad basica de filtros.
