# Tasks M31 Retrieval strategy gate

## 1. Setup

- [x] 1.1 Confirm PR #125 is merged in `origin/main`.
- [x] 1.2 Create branch `codex/m31-retrieval-strategy-gate`.
- [x] 1.3 Validate and archive `m30-qwen-sparse-dense-sparse`.
- [x] 1.4 Add OpenSpec proposal, design, tasks and spec deltas.

## 2. Gate runner

- [x] 2.1 Add failing tests for strategy gate decisions and serialization.
- [x] 2.2 Implement `StrategyGateReport`, decision rows and stable serializer.
- [x] 2.3 Compare dense, lexical, hybrid RRF, dense_sparse, graph and rerank.
- [x] 2.4 Mark graph `hold` unless live operational evidence exists elsewhere.

## 3. Contextual dense support

- [x] 3.1 Add failing dataset test for `contextual_summary`.
- [x] 3.2 Parse optional `contextual_summary` in eval evidence.
- [x] 3.3 Let fixture projects embed contextual summary plus chunk text.
- [x] 3.4 Emit `needs_more_data` for `contextual_dense` when suites lack summaries.

## 4. CLI and docs

- [x] 4.1 Add failing CLI integration test for `evals strategy-gate`.
- [x] 4.2 Implement `adaptive-rag evals strategy-gate`.
- [x] 4.3 Update progress and roadmap docs for M31.

## 5. Validation and PR

- [x] 5.1 Run targeted strategy gate, eval and CLI tests.
- [x] 5.2 Run full Python checks and OpenSpec validation.
- [x] 5.3 Commit, push and open a draft PR.
