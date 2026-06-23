# M27 Post-v1 retrieval expansion

M27 reopens advanced retrieval after the v1 product quality gate. The objective
is not to change the default immediately. The objective is to make the backend
capabilities real and measurable before frontend polish.

## Decision

Advanced retrieval proceeds as opt-in functionality:

1. M28 Contextual Retrieval generated summaries.
2. M29 Postgres lexical retrieval and RRF.
3. M30 Qwen sparse / `dense_sparse`.
4. M31 Retrieval strategy gate.

`dense` stays default until M31 proves another strategy should be promoted.

## Why this order

Contextual Retrieval reuses existing fields and input builders, so it has the
least blast radius. Lexical/RRF is local and addresses exact identifier misses
before hosted sparse complexity. Sparse retrieval requires current provider
documentation, storage/scoring decisions and cost evidence, so it comes after
the local fusion path.

## Frontend implication

Frontend polish should wait until M31 or explicitly exclude advanced retrieval
modes. Otherwise the UI would expose unstable or partially implemented backend
contracts.
