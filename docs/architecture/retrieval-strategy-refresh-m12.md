# Decision refresh de retrieval M12

Fecha: 2026-06-20
Estado: decision para cerrar `m12-strategy-decision-refresh`

## Comando ejecutado

Se ejecuto el runner interno `run_candidate_limit_ab_retrieval_eval_suite` sobre:

- suite: `evals/fixtures/retrieval-dataset-pack.json`
- provider: embeddings deterministas por eje, alineados con la fixture M12
- reranker: `FakeRerankProvider`
- modo: `offline`
- `candidate_limits`: `3`, `5`, `8`
- DB: SQLite in-memory con las tablas minimas de retrieval fixture

El objetivo era decidir si la evidencia ampliada justifica lexical/RRF, sparse
retrieval o presets/defaults nuevos de candidate tuning.

## Resultado agregado

Dense baseline:

| Metrica | Valor |
| --- | ---: |
| `retrieval_case_count` | 10 |
| `retrieval_passed_count` | 10 |
| `retrieval_hit_rate` | 1.0 |

Comparacion por limite:

| `candidate_limit` | Hit rate reranked | Delta vs dense | Improvements | Regressions | Ties | Best-rank delta avg | Status |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 3 | 1.0 | 0.0 | 0 | 1 | 9 | -0.1 | `passed` |
| 5 | 1.0 | 0.0 | 0 | 1 | 9 | -0.1 | `passed` |
| 8 | 1.0 | 0.0 | 0 | 1 | 9 | -0.1 | `passed` |

## Regresion observada

Los tres limites produjeron una regresion de ranking en
`distractor-realtime-quota-code`.

El caso siguio pasando porque el expected evidence no se perdio, pero el
`best_rank_delta_avg` quedo negativo y la familia `semantic_distractor` registro
1 regression, 0 improvements y 3 ties. Eso es suficiente para bloquear presets
o defaults nuevos: la mejora agregada es cero y hay una senal de degradacion por
caso.

Conteo por `risk_family` para cada limite:

| `risk_family` | Regressions | Improvements | Ties |
| --- | ---: | ---: | ---: |
| `identifier_exact` | 0 | 0 | 3 |
| `metadata_guard` | 0 | 0 | 1 |
| `multi_evidence` | 0 | 0 | 1 |
| `rerank_regression` | 0 | 0 | 1 |
| `semantic_distractor` | 1 | 0 | 3 |

## Decision matrix

| Opcion | Estado M12 | Decision |
| --- | --- | --- |
| Candidate tuning presets/defaults | `no-go` | No hay mejora frente a dense baseline y existe regresion de ranking en un semantic distractor. Mantener la superficie opt-in existente sin presets nuevos. |
| Lexical/RRF | `hold` | La suite ya contiene lexical misses versionados, pero el baseline determinista pasa esos casos. Todavia falta un fallo medido que lexical/RRF resuelva. |
| Qwen sparse retrieval | `hold` | No hay gap medido que requiera sparse, y cualquier adapter necesita docs provider actuales, storage/reindex y costo antes de diseno. |
| Dense retrieval default | `proceed` | Mantener dense como default: pasa 10/10 en la suite ampliada y no requiere providers ni indexes nuevos. |

## Cierre

M12 no habilita nuevos algoritmos ni defaults. La evidencia actual justifica:

- conservar dense retrieval como default;
- mantener rerank/candidate tuning solo como opt-in;
- no abrir lexical/RRF hasta observar fallos lexicales reales;
- no abrir sparse retrieval sin docs provider actuales y un gap medido.

