# Tasks M28 contextual retrieval generated summaries

## 1. Setup

- [x] 1.1 Confirm M27 PR is merged and archived.
- [x] 1.2 Create branch `codex/m28-contextual-retrieval-generated-summaries`.
- [x] 1.3 Add OpenSpec proposal, design, tasks and spec deltas.

## 2. Contextualization pipeline

- [x] 2.1 Add failing tests for deterministic context generation and idempotency.
- [x] 2.2 Implement local contextualizer and project-scoped pipeline.
- [x] 2.3 Persist summaries on existing chunks without changing original text.

## 3. First-run integration

- [x] 3.1 Add failing CLI/report tests for contextualized counts.
- [x] 3.2 Run contextualization after chunking and before dense embeddings.
- [x] 3.3 Update first-run and quality-gate docs with the new evidence fields.

## 4. Validation and PR

- [x] 4.1 Run targeted tests for contextualization, first-run and retrieval citation behavior.
- [x] 4.2 Run Python static checks and OpenSpec validation.
- [x] 4.3 Commit, push and open a draft PR.
