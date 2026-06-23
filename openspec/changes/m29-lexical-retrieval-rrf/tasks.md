# Tasks M29 lexical retrieval RRF

## 1. Setup

- [x] 1.1 Confirm M28 PR is merged in `origin/main`.
- [x] 1.2 Create branch `codex/m29-lexical-retrieval-rrf`.
- [x] 1.3 Archive `m28-contextual-retrieval-generated-summaries`.
- [x] 1.4 Add OpenSpec proposal, design, tasks and spec deltas.

## 2. Lexical retriever

- [x] 2.1 Add failing tests for lexical ranking over chunk lexical input.
- [x] 2.2 Add failing tests for metadata filters and original citations.
- [x] 2.3 Implement `LexicalRetriever` with PostgreSQL full-text and SQLite fallback.

## 3. Hybrid RRF

- [x] 3.1 Add failing service tests for `strategy=lexical`.
- [x] 3.2 Add failing service tests for `strategy=hybrid_rrf`.
- [x] 3.3 Implement strategy validation, lexical service path and RRF fusion.
- [x] 3.4 Serialize retrieval metadata and preserve audit scores.

## 4. Surfaces and evals

- [x] 4.1 Add API and CLI tests for lexical and hybrid strategies.
- [x] 4.2 Add offline eval CLI test for `--retrieval-strategy`.
- [x] 4.3 Expose strategies in API/CLI/eval schemas and docs.

## 5. Validation and PR

- [x] 5.1 Run targeted retrieval/API/CLI/eval tests.
- [x] 5.2 Run full Python checks and OpenSpec validation.
- [x] 5.3 Commit, push and open a draft PR.
