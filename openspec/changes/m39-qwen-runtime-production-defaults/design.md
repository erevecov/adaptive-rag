# Design M39 Qwen runtime production defaults

## Context

M33-M35 dejaron runtime settings operable: provider connections globales,
secrets cifrados, slots fijos, catalogo de modelos y acceptance fake local.
M38 agrego settings efectivos de retrieval para chat. El objetivo de M39 es
cerrar la ruta Qwen productiva sin romper esos contratos: Qwen debe quedar
facil de configurar y auditar, pero nunca debe activarse por sorpresa en CI,
tests o first-run local.

El repo ya usa los modelos Qwen siguientes como contrato operativo:

- `qwen-plus` para chat con tool calling.
- `text-embedding-v4` para dense embeddings.
- `text-embedding-v4` para sparse embeddings por DashScope native TextEmbedding.
- `qwen3-rerank` para rerank.

## Runtime Module Split

`adaptive_rag.provider_runtime` se mantiene como facade publico para evitar
romper imports existentes. La implementacion se separa en modulos internos:

- `adaptive_rag.runtime.resolution`: resuelve slots efectivos desde project
  override, default global o fallback `.env`.
- `adaptive_rag.runtime.factories`: construye providers/runners desde un
  `ResolvedRuntimeSlot`.
- `adaptive_rag.runtime.qwen_defaults`: declara defaults Qwen production,
  capability inference y la materializacion idempotente de defaults faltantes.

El facade reexporta `ProviderConfigurationError`, `ResolvedRuntimeSlot`,
`get_dense_embedding_provider`, `get_sparse_embedding_provider`,
`get_chat_runner`, `get_rerank_provider` y `get_contextualizer`.

## Qwen Auto Defaults

No hay comando obligatorio de bootstrap. Si una Qwen connection ya esta
conectada y el usuario dispara el sync normal de modelos, el backend
materializa defaults faltantes desde el catalogo sincronizado.

Entradas:

- Provider connections Qwen existentes, con `base_url`, capabilities y secret
  `api_key` persistido o fallback runtime disponible.
- Catalogo resultante de model sync para esas connections.

Salidas:

- Pool global de chat con `qwen-plus` como default solo si el pool global esta
  vacio.
- Default global de `dense_embedding` con `text-embedding-v4` solo si el slot no
  tiene default existente y el modelo esta catalogado para dense.
- Default global de `sparse_embedding` con `text-embedding-v4` solo si el slot
  no tiene default existente, el modelo esta catalogado para sparse y la
  connection usa DashScope native TextEmbedding. Una base OpenAI-compatible no
  sirve para sparse.
- Default global de `rerank` con `qwen3-rerank` solo si el slot no tiene default
  existente y el modelo esta catalogado para rerank.

La materializacion es idempotente: repetir sync no duplica rows y no reemplaza
defaults ni pool de chat que el usuario ya eligio. Tampoco crea provider
connections nuevas, guarda API keys desde environment ni llama red fuera del
model sync solicitado.

## Capability Inference

El catalogo no debe tratar todos los modelos de una connection como compatibles
con todas sus capabilities cuando el provider no devuelve capabilities. Para
Qwen se infieren capabilities por `model_id` conocido:

- `qwen-plus`, `qwen-max`, `qwen-turbo` y modelos `qwen3-*` instruct/chat:
  `chat`.
- `text-embedding-v4` y `text-embedding-v3`: `dense_embedding` y
  `sparse_embedding`.
- IDs que contienen `rerank`: `rerank`.

Si un modelo Qwen no coincide, el sync puede usar capabilities devueltas por el
provider; si tampoco existen, el modelo queda con capabilities vacias y no se
ofrece para slots hasta que el usuario lo catalogue explicitamente en un cambio
posterior. Para `fake` se conserva el catalogo determinista actual. Para
`local_openai_compatible`, se mantiene el comportamiento existente porque no hay
un naming contract universal.

## Error Handling

Errores estables nuevos o reutilizados:

- `missing_provider_secret`
- `missing_provider_base_url`

Ningun error debe incluir API keys, Authorization headers, ciphertext ni
payloads provider completos.

## Testing

La implementacion sigue TDD:

1. Tests RED de capability inference Qwen en model sync.
2. Tests RED de materializacion idempotente sobre SQLite in-memory.
3. Tests RED de API sync que prueben que conectar/sincronizar Qwen deja
   defaults faltantes listos para uso.
4. Refactor del runtime facade solo despues de mantener tests verdes.
5. Quality gate backend/frontend relevante y OpenSpec strict.
