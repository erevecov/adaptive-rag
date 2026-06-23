# Post-v1 Retrieval Expansion Design

## Goal

Prepare advanced retrieval capabilities before frontend polish, while preserving
the validated v1 product default: `dense` retrieval remains the default path
until a later quality gate proves another strategy improves quality without
critical regressions.

## Decision

The expansion track is opt-in and evidence-driven. M27 opens the scope and
sequence; M28-M31 implement and evaluate capabilities in separate PRs.

Recommended order:

1. **M28 Contextual Retrieval generated summaries.** The schema already carries
   `contextual_summary`, and embedding input construction already knows how to
   prepend it. This is the lowest-risk first capability because it improves the
   existing dense path without adding a new ranking index.
2. **M29 Lexical retrieval and RRF.** Postgres full-text plus reciprocal rank
   fusion should cover exact identifiers, names and code-like terms locally,
   without hosted provider dependency.
3. **M30 Qwen sparse / `dense_sparse`.** Sparse retrieval uses the reserved
   `chunk_sparse_embeddings` schema and `dense_sparse` project mode, but must
   verify current provider docs before defining payloads, scoring, reindex or
   costs.
4. **M31 Retrieval strategy gate.** Compare dense, contextual dense, lexical,
   sparse, RRF, graph opt-in and rerank. Only this gate can recommend promoting
   a strategy beyond opt-in.

## Scope

In scope:

- OpenSpec plan for the post-v1 retrieval expansion track.
- Docs updates that make the sequence explicit before frontend polish.
- Requirements that prevent hidden default changes.
- Requirements that every capability has API/CLI/eval evidence before UI work
  depends on it.

Out of scope for M27:

- Implementing contextualizer code.
- Adding Postgres full-text indexes or RRF ranking.
- Calling Qwen sparse provider endpoints.
- Promoting graph, sparse, lexical or contextual retrieval to default.
- Frontend polish.

## Architecture

The track keeps the existing retrieval boundary:

- `RetrievalService` remains the coordination layer for public API/CLI behavior.
- Dense retrieval remains the baseline and fallback.
- Contextualization enriches chunk metadata and embedding inputs before
  retrieval.
- Lexical and sparse retrieval are independent candidate-producing branches.
- RRF combines candidate lists that already respect project isolation,
  metadata filters and citation contracts.
- Rerank remains an optional final stage over bounded candidate lists.

Every new branch must return enough metadata for audit and eval reporting:
strategy name, fallback reason, scores, candidate counts, filters applied and
citation coverage.

## Data Flow

Default path remains:

1. Author project/source.
2. Ingest source.
3. Chunk document version.
4. Build dense embedding inputs.
5. Run dense retrieval.
6. Chat cites original chunk text.

Post-v1 opt-in branches add:

- Contextualizer: generates `contextual_summary` before embedding.
- Lexical: indexes/searches `lexical_input_text` through Postgres full-text.
- Sparse: stores sparse vectors in `chunk_sparse_embeddings` and scores overlap
  for projects using `embedding_mode = dense_sparse`.
- RRF: fuses candidate lists from dense, lexical and sparse branches.

## Error Handling

- Missing hosted credentials must fail before network calls.
- Contextualization failures must make ingestion/indexing state actionable and
  retryable, not silently degrade citations.
- Lexical/sparse/RRF must preserve dense fallback with stable `fallback_reason`
  values.
- Sparse provider errors must not leave half-written sparse rows without an
  observable reindex path.

## Testing

Each implementation milestone must include:

- Unit tests for contracts and scoring.
- Integration tests against SQLite or Postgres where the feature requires SQL
  behavior.
- API/CLI tests for public controls.
- Offline eval coverage for strategy comparison.
- OpenSpec validation.

M31 must produce a decision report that can say `promote`, `keep_opt_in`,
`hold`, `no_go` or `needs_more_data` per strategy.

## Review Notes

This design intentionally avoids frontend polish until the retrieval capability
surface is stable. Frontend work can then expose known modes instead of chasing
backend churn.
