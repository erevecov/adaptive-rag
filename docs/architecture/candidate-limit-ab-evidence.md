# Evidencia A/B de candidate limit M11

Fecha: 2026-06-20
Estado: decision para cerrar `m11-candidate-limit-api-cli-surface`

## Comando ejecutado

Se ejecuto el runner interno `run_candidate_limit_ab_retrieval_eval_suite` sobre:

- suite: `evals/fixtures/retrieval-dataset-pack.json`
- provider: `FakeDenseEmbeddingProvider`
- reranker: `FakeRerankProvider`
- modo: `offline`
- `candidate_limits`: `3`, `5`, `8`
- DB: SQLite in-memory con las tablas minimas de retrieval fixture

El objetivo era decidir si la evidencia justificaba una nueva superficie
API/CLI o presets publicos para candidate tuning.

## Resultado agregado

Dense baseline:

| Metricas | Valor |
| --- | ---: |
| `retrieval_case_count` | 7 |
| `retrieval_passed_count` | 4 |
| `retrieval_hit_rate` | 0.5714 |

Comparacion por limite:

| `candidate_limit` | Hit rate reranked | Delta vs dense | Improvements | Regressions | Ties | Status |
| ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 3 | 0.4286 | -0.1429 | 2 | 1 | 4 | `failed` |
| 5 | 0.4286 | -0.1429 | 3 | 1 | 3 | `failed` |
| 8 | 0.8571 | 0.2857 | 5 | 1 | 1 | `failed` |

## Regresion critica

Los tres limites produjeron una regresion en
`distractor-alpha-release-notes`: dense pasaba el caso y rerank lo degrado,
perdiendo `api-error-fields`.

Esa regresion importa porque el dataset pack marca distractors como riesgo
representativo. Un preset publico que mejore el hit rate agregado pero degrade
un distractor todavia no cumple el gate de M10/M11 para cambiar o recomendar
parametros.

## Decision

Estado de `m11-candidate-limit-api-cli-surface`: `hold`.

No se agrega una nueva superficie API/CLI ni preset M11 para candidate tuning.
La razon es:

- `candidate_limit=8` mejora el hit rate agregado, pero mantiene una regresion
  por caso.
- `candidate_limit=3` y `5` empeoran el hit rate agregado frente a dense.
- La corrida fue offline; no aporta costo/latencia hosted suficiente para
  recomendar un knob o preset nuevo.
- La superficie opt-in de rerank ya existe desde M9; no hace falta duplicarla
  sin evidencia mas fuerte.

## Cierre

`m11-quality-gate` se ejecuto y archivo
`m11-retrieval-strategy-decision` como:

- `openspec/changes/archive/2026-06-20-m11-retrieval-strategy-decision/`

Durante el quality gate, el hosted eval Qwen reranked con `candidate_limit=8`
paso los 7 casos de `retrieval-dataset-pack` sin regresiones live. Esa evidencia
valida el provider/rerank opt-in, pero no cambia la decision de no publicar
presets nuevos en M11: dense retrieval sigue siendo el default y cualquier
experimento posterior debe abrir otro change OpenSpec.
