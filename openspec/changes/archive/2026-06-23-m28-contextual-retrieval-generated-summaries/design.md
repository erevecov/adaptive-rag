# Design M28 contextual retrieval generated summaries

## Context

M3 reserved `chunks.contextual_summary` and taught the embedding input builder
to prepend it to `embedding_input_text` and `lexical_input_text`. M28 activates
that reserved surface without changing retrieval strategy selection.

## Approach

Create a small contextualization module with three pieces:

1. `GeneratedContextualSummary`: immutable output with the generated summary
   and deterministic metadata.
2. `DeterministicContextualizer`: local fake/default generator that uses
   document title/section metadata plus the chunk text to produce stable,
   bounded context without network access.
3. `ContextualizationPipeline`: project-scoped pipeline that lists chunks for a
   document version, skips chunks that already have `contextual_summary`, and
   persists summaries before embedding.

The first-run smoke calls contextualization after chunking and before dense
embedding. The existing embedding pipeline then rehashes and embeds
`contextual_summary + chunk_text`.

## Contract

- Idempotency is field-based for M28: a non-empty `contextual_summary` is
  reused.
- Generated summaries are stored only in `chunks.contextual_summary`; original
  citation snippets still come from `document_versions.normalized_text`.
- The report exposes `contextualized_chunk_count` and
  `reused_contextualized_chunk_count`.
- Hosted model contextualization can be added later behind the same interface,
  but M28 must remain fully local.

## Alternatives Considered

- Hosted Qwen contextualization now: rejected because M30 already owns provider
  doc verification and sparse/provider-specific assumptions.
- Embedding-time only context without persistence: rejected because M29 lexical
  and M31 gate need a stable indexed field to inspect and compare.
- Regenerating summaries every run: rejected because it would make embedding
  hashes unstable when a future generator changes.

## Risks

- Deterministic local summaries are not as rich as LLM summaries. Mitigation:
  M28 proves plumbing and stable contracts; later provider-backed generation can
  replace the generator without changing storage.
- Context could leak into citations. Mitigation: retrieval citations already use
  original text slices; tests preserve that behavior.
