# Proposal M28 contextual retrieval generated summaries

## Why

M27 made advanced retrieval an opt-in post-v1 track and selected generated
Contextual Retrieval as the first implementation milestone. The schema already
has `chunks.contextual_summary`, and the dense embedding input builder already
uses it when present, but no indexing path generates that field.

## What Changes

- Add a local deterministic contextualization pipeline that generates
  `contextual_summary` for existing chunks before embeddings are created.
- Make contextualization idempotent and project-scoped.
- Wire the first-run smoke so it reports contextualized chunks and proves the
  generated context is used by the embedding path.
- Keep dense retrieval as the default strategy; this change does not add a new
  ranking branch or promote contextual retrieval through frontend defaults.

## Out of Scope

- Lexical retrieval, RRF, sparse retrieval and Qwen sparse payloads.
- Hosted LLM calls for contextualization.
- Frontend mode controls or visual polish.
- Changing the citation text to include generated summaries.

## Validation

- Unit tests for generated context and idempotency.
- First-run CLI integration test for the new report fields.
- Existing embedding tests proving contextual summaries affect input hashes.
- OpenSpec strict validation and standard Python checks.
