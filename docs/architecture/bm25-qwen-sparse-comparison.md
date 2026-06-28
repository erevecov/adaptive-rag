# BM25 vs Qwen Sparse Comparison

Fecha: 2026-06-28

## Decision

`bm25` queda disponible como estrategia local opt-in para medir Okapi BM25
contra `sparse` y `dense_sparse`, las alternativas con sparse embeddings de
Qwen/DashScope. Con evidencia live Qwen, `dense_sparse` es la alternativa que
vale seguir evaluando; BM25 y `sparse` puro quedan como opt-in/baseline porque
ambos introducen la misma regresion frente a dense. `dense_sparse` queda
promovido como default; `dense` sigue disponible como baseline explicito.

## Alcance

- `strategy=bm25` usa el mismo input contextualizado que lexical retrieval.
- BM25 corre localmente, sin dense embeddings, sparse embeddings ni provider
  hosted.
- `strategy=sparse` mide la senal sparse aislada sin fusionarla con dense.
- `strategy=dense_sparse` fusiona dense y sparse con RRF cuando el runtime
  configura Qwen; en offline/fake usa el provider sparse fake existente.
- `adaptive-rag evals strategy-gate <suite>` compara BM25, sparse y
  dense_sparse en el mismo reporte.

## Comando de medicion

```powershell
uv run adaptive-rag evals strategy-gate evals/fixtures/retrieval-dataset-pack.json
```

Para medir Qwen sparse real, el runtime debe tener provider live y
`sparse_embedding` configurado con Qwen antes de ejecutar el gate. Sin esa
configuracion, las ramas `sparse` y `dense_sparse` usan el fake local y sirven
solo como smoke determinista.

Config minima para la corrida live:

```powershell
$env:ADAPTIVE_RAG_PROVIDER_RUNTIME_MODE = "live"
$env:ADAPTIVE_RAG_EMBEDDING_PROVIDER = "qwen"
$env:ADAPTIVE_RAG_EMBEDDING_MODEL = "text-embedding-v4"
$env:ADAPTIVE_RAG_SPARSE_EMBEDDING_PROVIDER = "qwen"
$env:ADAPTIVE_RAG_SPARSE_EMBEDDING_MODEL = "text-embedding-v4"
$env:ADAPTIVE_RAG_QWEN_BASE_URL = "https://dashscope-intl.aliyuncs.com/api/v1/services/embeddings/text-embedding/text-embedding"
$env:ADAPTIVE_RAG_QWEN_API_KEY = "<secret>"
$env:ADAPTIVE_RAG_PROVIDER_MAX_COST_USD = "0.05"
uv run adaptive-rag evals strategy-gate evals/fixtures/retrieval-dataset-pack.json --require-live-qwen-sparse --output reports/bm25-qwen-sparse-live.json
```

Cuando el CLI registra llamadas live, el JSON incluye `provider_usage` agregado
por provider/model/operacion, sin request ids ni secretos.

Nota operativa: DashScope `text-embedding-v4` acepta hasta 10 textos por
request. El cliente Qwen parte dense y sparse embeddings en batches de 10 para
que el gate pueda correr sobre suites mayores.

## Resultado live Qwen 2026-06-28

Runtime observado:

- `provider_runtime_mode=live`
- `embedding_provider=qwen`
- `sparse_embedding_provider=qwen`
- `embedding_model=text-embedding-v4`
- `sparse_embedding_model=text-embedding-v4`
- endpoint nativo DashScope TextEmbedding

Suite: `evals/fixtures/retrieval-dataset-pack.json`.

Salida JSON: `%TEMP%/adaptive-rag-strategy-gate-live-qwen-focused.json`.

| Strategy | Hit rate | MRR@k | nDCG@k | Passed | Delta hit | Delta MRR | Delta nDCG | Improvements | Regressions | Decision |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| dense | 1.0 | 0.95 | 0.963 | 10 / 10 | n/a | n/a | n/a | n/a | n/a | baseline |
| bm25 | 0.9 | 0.85 | 0.863 | 9 / 10 | -0.1 | -0.1 | -0.1 | 0 | 1 | no_go |
| sparse | 0.9 | 0.85 | 0.863 | 9 / 10 | -0.1 | -0.1 | -0.1 | 0 | 1 | no_go |
| dense_sparse | 1.0 | 0.95 | 0.963 | 10 / 10 | 0.0 | 0.0 | 0.0 | 0 | 0 | promote |

Regresion compartida de BM25 y `sparse`: `distractor-alpha-release-notes`
pierde `api-error-fields`. `dense_sparse` no introduce regresiones y empata al
baseline dense en esta suite, por lo que se promueve como default Qwen.

`provider_usage`: 58 llamadas Qwen embeddings, 58 exitosas, 0 fallidas, 1,000
tokens totales reportados, 72 inputs. El costo estimado queda `null` porque la
corrida no tenia precio de embedding configurado en el catalogo local.

Lectura: sobre esta suite, BM25 no supera a la alternativa Qwen cuando Qwen se
mide de verdad. BM25 sigue siendo util como baseline local barato y explicable,
pero no conviene promoverlo sobre dense ni sobre `dense_sparse`. La ruta
recomendada es `dense_sparse`, no `sparse` puro.

## Resultado local 2026-06-28

Runtime observado:

- `provider_runtime_mode=fake`
- `embedding_provider=fake`
- `sparse_embedding_provider=fake`

Suite: `evals/fixtures/retrieval-dataset-pack.json`.

| Strategy | Hit rate | MRR@k | nDCG@k | Passed | Delta hit | Delta MRR | Delta nDCG | Improvements | Regressions | Decision |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| dense | 0.4 | 0.35 | 0.363 | 4 / 10 | n/a | n/a | n/a | n/a | n/a | no_go |
| bm25 | 0.9 | 0.85 | 0.863 | 9 / 10 | +0.5 | +0.5 | +0.5 | 7 | 1 | no_go |
| sparse | 0.9 | 0.8 | 0.826 | 9 / 10 | +0.5 | +0.45 | +0.463 | 6 | 1 | no_go |
| dense_sparse | 0.8 | 0.633 | 0.683 | 8 / 10 | +0.4 | +0.283 | +0.32 | 6 | 0 | no_go |

Lectura: BM25 local empata a `sparse` fake en hit rate y queda por encima en
MRR/nDCG. Ambos ganan contra `dense_sparse` fake en este fixture, pero
introducen una regresion en
`distractor-alpha-release-notes`. La medicion local/fake sigue siendo una smoke
determinista; la decision de default se toma con la corrida live Qwen.
