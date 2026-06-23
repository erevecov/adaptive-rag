# Design M29 lexical retrieval RRF

## Context

Dense retrieval remains the default. M28 made contextual summaries durable, and
the embedding input builder already defines lexical input as the same text used
for dense embeddings: generated context when present plus original chunk text.

M29 should make lexical/RRF usable before frontend polish, but it should not
add a new default or a new provider dependency.

## Approach

1. Add `LexicalRetriever` beside `DenseRetriever`.
2. Use PostgreSQL full-text functions when running against Postgres and a
   deterministic token-overlap fallback for SQLite/unit tests.
3. Convert lexical hits into normal retrieval results with original citations.
4. Add `hybrid_rrf` in `RetrievalService` by running dense and lexical candidate
   lists, fusing ranks with `1 / (60 + rank)`, and ordering by RRF score plus
   stable chunk id.
5. Add optional `retrieval_metadata` to result payloads with dense, lexical and
   RRF scores/ranks.
6. Let the existing rerank layer re-rank the selected strategy candidates when
   explicitly requested.

## Contract

- `dense` remains the default.
- `lexical` and `hybrid_rrf` require explicit `strategy` selection.
- `metadata_filter` is applied before ranking in dense, lexical and hybrid.
- Citations always use original normalized document text, not generated
  contextual summaries.
- If a chunk appears in both dense and lexical lists, RRF emits one result with
  combined score metadata.
- Offline evals can run with `--retrieval-strategy lexical` or
  `--retrieval-strategy hybrid_rrf`.

## Risks

- Query-time lexical scoring can become slow on large corpora. Mitigation: M29
  is an opt-in contract slice; materialized tsvector/index work can follow
  after M31 reports that lexical/RRF should stay.
- SQLite fallback scoring will not exactly match PostgreSQL ts_rank. Mitigation:
  tests assert ordering contracts and filter/citation behavior, not exact
  provider-specific rank math.
