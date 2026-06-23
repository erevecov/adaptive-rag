# Proposal M29 lexical retrieval RRF

## Why

M27 set the post-v1 sequence and M28 now persists contextual summaries before
embedding. The next low-risk retrieval capability is local lexical retrieval and
RRF over local candidate lists. This targets exact identifiers, codes and names
that dense retrieval can miss, without introducing hosted provider assumptions.

## What Changes

- Add opt-in `lexical` retrieval over chunk lexical input text.
- Add opt-in `hybrid_rrf` retrieval that fuses dense and lexical candidate
  ranks with reciprocal rank fusion.
- Preserve project isolation, metadata filters, stable ordering and original
  citation snippets.
- Expose both strategies through API, CLI and offline eval execution.
- Serialize retrieval score metadata so audit/history can preserve lexical and
  RRF scores.

## Out of Scope

- Promoting lexical or RRF to default.
- New frontend controls.
- Qwen sparse or provider-specific sparse payloads.
- New materialized lexical index tables or migrations. M29 computes lexical
  input from existing chunk/document fields; materialization can be added after
  M31 if the strategy gate justifies it.

## Validation

- Unit tests for lexical ranking, filters and RRF fusion.
- API/CLI integration tests for `strategy=lexical` and `strategy=hybrid_rrf`.
- Offline eval CLI test for retrieval strategy selection.
- OpenSpec strict validation and standard Python checks.
