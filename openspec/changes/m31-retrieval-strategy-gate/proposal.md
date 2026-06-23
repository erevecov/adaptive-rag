# Proposal M31 Retrieval strategy gate

## Why

M28-M30 dejaron listas las capacidades backend antes de pulir frontend:
contextual summaries, lexical/RRF y Qwen sparse / `dense_sparse`. Falta el
contrato que impide promover modos por intuicion: un gate offline que compare
las estrategias listas contra `dense`, reporte regresiones y emita una decision
por estrategia.

## What Changes

- Add an offline retrieval strategy gate runner for `dense`,
  `contextual_dense`, `lexical`, `hybrid_rrf`, `dense_sparse`, `graph` and
  `dense_rerank`.
- Add stable JSON decisions per strategy: `promote`, `keep_opt_in`, `hold`,
  `no_go` or `needs_more_data`.
- Add `adaptive-rag evals strategy-gate <suite>` as the CLI surface.
- Allow eval evidence to carry optional `contextual_summary` so
  `contextual_dense` can be measured when a suite contains contextual evidence.
- Archive M30 and update roadmap/progress docs to make M31 active.

## Non-Goals

- Changing the default retrieval strategy in this PR.
- Adding frontend controls or frontend polish.
- Running hosted providers by default.
- Replacing the existing graph live evidence gate; graph remains `hold` without
  operational evidence.

## Validation

- Unit tests for strategy gate decisions, serialization and contextual summary
  parsing.
- CLI integration test for `evals strategy-gate`.
- Full Python checks and OpenSpec validation.
