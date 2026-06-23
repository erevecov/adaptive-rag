# Design M27 retrieval expansion plan

## Context

M10-M12 established evidence gates for retrieval changes. Their decision was
correct for v1: dense stayed default, candidate tuning presets were `no-go`,
and lexical/RRF plus sparse retrieval stayed in `hold`.

The product goal has now changed. V1 is ready, and the next scope is to finish
advanced retrieval functionality before polishing the frontend. M27 therefore
opens an opt-in capability track without promoting any mode by default.

## Approach

Use a staged OpenSpec track:

1. **M28 Contextual Retrieval.** Generate `contextual_summary` during indexing,
   reuse existing `embedding_input_text` and `lexical_input_text` construction,
   and measure dense with/without context.
2. **M29 Lexical/RRF.** Add local Postgres full-text retrieval over
   `lexical_input_text`, then RRF over candidate lists that already preserve
   project filters and citations.
3. **M30 Qwen sparse.** Verify current provider docs, then implement sparse
   embedding storage/scoring for `dense_sparse` projects as opt-in.
4. **M31 Strategy gate.** Compare dense, contextual dense, lexical, sparse,
   hybrid RRF, graph opt-in and rerank. Decide promote/keep opt-in/hold/no-go.

## Interface Principles

- `dense` remains default and fallback.
- Every new mode is explicit in API/CLI/evals.
- API/CLI controls should be stable before frontend polish.
- Each candidate branch returns strategy metadata, scores, fallback reason,
  applied filters and citation coverage.
- Hosted provider paths remain budgeted and secret-safe.

## Sequencing Rationale

Contextual Retrieval comes first because the schema and embedding input builder
already reserve the required shape. It improves the existing dense path without
adding a new candidate source.

Lexical/RRF comes second because it is local, cheap and directly targets exact
identifier failures. It also creates the fusion contract needed before sparse.

Sparse comes third because it depends on provider-specific payloads, storage,
scoring and reindex semantics. It should not be designed from memory.

The strategy gate comes last because individual capabilities can look useful in
isolation while still degrading citations, filters, latency or cost.

## Testing

Each implementation milestone must include unit tests, API/CLI tests, eval
coverage and OpenSpec validation. M31 must produce a machine-readable decision
report with per-strategy status.

## Risks

- Advanced modes could become defaults by inertia. Mitigation: M27 explicitly
  blocks promotion until M31.
- Sparse provider docs may have changed. Mitigation: M30 must verify current
  docs before coding payload/storage assumptions.
- Frontend may start before backend contracts settle. Mitigation: roadmap puts
  frontend polish after M31.
