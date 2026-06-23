# Tasks M30 Qwen sparse dense_sparse

## 1. Setup

- [x] 1.1 Confirm PR #124 is merged in `origin/main`.
- [x] 1.2 Create branch `codex/m30-qwen-sparse-dense-sparse`.
- [x] 1.3 Verify current DashScope/Qwen sparse embedding docs.
- [x] 1.4 Archive `m29-lexical-retrieval-rrf`.
- [x] 1.5 Add OpenSpec proposal, design, tasks and spec deltas.

## 2. Sparse provider and pipeline

- [x] 2.1 Add failing tests for Qwen sparse embedding request/response parsing.
- [x] 2.2 Add sparse provider contract and fake/Qwen implementations.
- [x] 2.3 Add sparse embedding repository and pipeline tests.
- [x] 2.4 Implement idempotent sparse backfill using contextualized input.

## 3. Sparse retrieval and dense_sparse

- [x] 3.1 Add failing sparse retriever tests for score/filter/citation behavior.
- [x] 3.2 Add failing service tests for `strategy=dense_sparse`.
- [x] 3.3 Implement `SparseRetriever` and dense+sparse RRF fusion.
- [x] 3.4 Serialize sparse metadata and preserve audit sparse/RRF scores.

## 4. Surfaces and evals

- [x] 4.1 Add CLI sparse backfill tests.
- [x] 4.2 Add API/CLI retrieval tests for `strategy=dense_sparse`.
- [x] 4.3 Add offline eval CLI test for `--retrieval-strategy dense_sparse`.
- [x] 4.4 Update docs for sparse backfill and dense_sparse usage.

## 5. Validation and PR

- [x] 5.1 Run targeted provider/pipeline/retrieval/API/CLI/eval tests.
- [x] 5.2 Run migration, full Python checks and OpenSpec validation.
- [x] 5.3 Commit, push and open a draft PR.
