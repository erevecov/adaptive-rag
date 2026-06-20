# Decision de estrategia de retrieval M11

Fecha: 2026-06-20
Estado: decision inicial para abrir M11

## Decision

El primer experimento recomendado despues de M10 es tuning de
`candidate_limit` y limites relacionados de rerank.

Estado por opcion:

| Opcion | Estado | Motivo |
| --- | --- | --- |
| Tuning de `candidate_limit` | `proceed` | Menor blast radius: reutiliza dense/rerank, reportes A/B y smokes Qwen existentes. |
| Lexical/RRF | `hold` | Falta evidencia de fallos lexicales concretos y diseno de fusion con filtros/citations. |
| Qwen sparse retrieval | `hold` | Requiere docs provider actuales, storage/reindex y estimacion de costo antes de codificar. |

## Evidencia usada

- M10 publico `retrieval-dataset-pack`, `case_metadata`, `comparison_cases` y
  decision gates.
- `docs/architecture/retrieval-decision-gates.md` exige `proceed`, `hold`,
  `no-go` o `needs-more-data` antes de tocar retrieval productivo.
- La ruta Qwen sparse no debe asumir API syntax por memoria. En este PR,
  `ctx7` resolvio Model Studio y DashScope, pero el fetch de Model Studio no
  entrego detalles utiles de embeddings sparse. Por eso cualquier adapter Qwen
  sparse posterior debe verificar docs actuales de DashScope/Qwen en su propio
  PR antes de fijar payloads.

## Criterios para el siguiente slice

`m11-candidate-limit-eval-matrix` debe:

- comparar valores acotados de `candidate_limit` sobre suites versionadas;
- reportar metricas por `intent` y `difficulty` cuando existan;
- listar regresiones antes que mejoras;
- mantener offline como gate obligatorio;
- dejar hosted Qwen como opt-in con budget explicito;
- no cambiar defaults productivos.

## Criterios de no-go

El experimento debe volver a diseno si:

- baja `retrieval_hit_rate` frente a dense baseline;
- agrega regresiones en `exact_match`, `metadata_filter` o `multi_evidence`;
- aumenta costo/latencia sin mejora por caso;
- necesita un provider o index nuevo para explicar el resultado;
- cambia dense default sin otro quality gate.

