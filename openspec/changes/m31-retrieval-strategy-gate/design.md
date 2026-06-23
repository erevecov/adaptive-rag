# Design M31 Retrieval strategy gate

## Gate runner

Add `adaptive_rag.evals.strategy_gate_runner` as an eval-layer module. It builds
one fixture project for dense baseline and reuses `RetrievalService` for ready
strategies. The runner does not add ranking logic; it only orchestrates
existing branches and compares their reports.

The default comparison set is:

- `dense`
- `contextual_dense`
- `lexical`
- `hybrid_rrf`
- `dense_sparse`
- `graph`
- `dense_rerank`

`contextual_dense` is not a public `RetrievalStrategy`; it is a separate eval
fixture where evidence includes `contextual_summary` and dense embeddings are
built from summary plus chunk text. If a suite has no contextual summaries, the
row is skipped with `needs_more_data`.

## Decisions

The gate compares each candidate against dense baseline using hit rate delta,
case-level regressions, citation coverage and metadata filter pass counts.

- `promote`: candidate improves hit rate with no regressions.
- `keep_opt_in`: candidate matches dense with no regressions.
- `hold`: candidate passes quality but needs external operational evidence.
- `no_go`: candidate fails, regresses, loses citations or violates filters.
- `needs_more_data`: candidate cannot be evaluated from the current suite.

`dense` remains the default recommendation unless a non-dense strategy earns
`promote`. Graph uses `hold` after offline pass because M19/M20 require live
operational evidence before graph default promotion.

## CLI

Add `adaptive-rag evals strategy-gate <suite> [--output path]`. The command is
offline by default and emits stable JSON with:

- `dense_baseline`
- `strategy_decisions`
- `default_strategy`
- `recommended_default`

The command exits non-zero only when the gate report status is `failed`.

## Dataset support

Extend eval evidence with optional `contextual_summary`. Existing suites remain
valid. Unknown fields are still rejected.
