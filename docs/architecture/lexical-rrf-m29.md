# Lexical Retrieval and Hybrid RRF M29

Estado: opt-in implementado en M29. `dense` sigue siendo el default.

## Decision

M29 agrega dos estrategias de retrieval backend sin cambiar el comportamiento
por defecto:

- `lexical`: ranking local por full-text sobre el texto original mas
  `contextual_summary` cuando existe.
- `hybrid_rrf`: fusiona dense retrieval y lexical retrieval con Reciprocal Rank
  Fusion usando `k=60`.

La decision de promover o no alguna estrategia queda diferida a M31, donde se
compararan dense, contextual dense, lexical, sparse, graph opt-in y rerank con
evidencia de evals.

## Superficies

API y CLI de retrieval aceptan `strategy=dense|graph|lexical|hybrid_rrf`.
Offline evals aceptan `--retrieval-strategy` para correr suites reproducibles
con la misma estrategia backend.

Chat mantiene su ruta por defecto y no expone selector frontend en M29.

## Audit

Los payloads pueden incluir `retrieval_metadata` con ranks y scores de dense,
lexical y RRF. El audit trail persiste esos valores en las columnas existentes
`dense_score`, `lexical_score`, `rrf_score` y `rerank_score` cuando estan
disponibles.

## Limites

M29 no agrega migraciones, no crea un indice materializado, no integra sparse
retrieval y no cambia el default del producto. PostgreSQL usa full-text local;
SQLite mantiene un fallback deterministico para tests y ejecuciones offline.
