# M30 Qwen sparse dense_sparse

M30 agrega sparse embeddings como capacidad opt-in sin cambiar el default
`dense`.

## Alcance

- `adaptive-rag sparse backfill --project-id <project-id>` llena
  `chunk_sparse_embeddings` desde chunks ya creados.
- El backfill usa el mismo input contextualizado que dense/lexical:
  `contextual_summary + "\n\n" + chunk_text` cuando hay contexto, y `chunk_text`
  como fallback.
- `strategy=dense_sparse` ejecuta dense retrieval y sparse retrieval, deduplica
  por chunk y fusiona con Reciprocal Rank Fusion (`k=60`).
- API, CLI y evals offline aceptan `dense_sparse`.
- Audit/history preserva `sparse_score` cuando el resultado lo trae.

## Provider Qwen

Qwen sparse usa el endpoint native DashScope TextEmbedding, no el endpoint
OpenAI-compatible. El payload envia:

- `parameters.output_type = "sparse"`
- `parameters.text_type = "document"` para backfill
- `parameters.text_type = "query"` para retrieval
- `parameters.dimension = 1024`

El response esperado contiene `output.embeddings[].sparse_embedding[]` con
`index`, `value` y `token` opcional.

Config live minima:

```bash
ADAPTIVE_RAG_PROVIDER_RUNTIME_MODE=live
ADAPTIVE_RAG_EMBEDDING_PROVIDER=qwen
ADAPTIVE_RAG_EMBEDDING_MODEL=text-embedding-v4
ADAPTIVE_RAG_SPARSE_EMBEDDING_PROVIDER=qwen
ADAPTIVE_RAG_SPARSE_EMBEDDING_MODEL=text-embedding-v4
ADAPTIVE_RAG_QWEN_API_KEY=...
ADAPTIVE_RAG_QWEN_BASE_URL=https://dashscope-intl.aliyuncs.com/api/v1/services/embeddings/text-embedding/text-embedding
```

## Uso

```bash
uv run adaptive-rag sparse backfill --project-id <project-id>

uv run adaptive-rag retrieval search \
  --project-id <project-id> \
  --query "SKU-42 installation" \
  --strategy dense_sparse

uv run adaptive-rag evals run evals/fixtures/retrieval-smoke.json \
  --mode offline \
  --retrieval-strategy dense_sparse
```

## No cambios de default

M30 no promueve sparse ni `dense_sparse`. El default del producto sigue siendo
`dense`; M31 debe comparar dense, contextual dense, lexical, sparse, hybrid RRF,
graph opt-in y rerank antes de decidir promocion.
