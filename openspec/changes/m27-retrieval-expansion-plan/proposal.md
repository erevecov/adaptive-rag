# Proposal M27 retrieval expansion plan

## Why

V1 is now release-ready as a local-first product, but advanced retrieval
capabilities remain deferred. Before frontend polish, we want the backend
capability surface to be stable enough that the UI can expose real modes rather
than chase backend churn.

Prior retrieval gates kept lexical/RRF and Qwen sparse in `hold` because they
should not enter the default product by inertia. This change reopens them with a
different objective: make them functional as opt-in experimental capabilities,
then decide later whether any deserve promotion.

## What Changes

- Add the `m27-retrieval-expansion-plan` OpenSpec change.
- Define the post-v1 retrieval sequence:
  1. M28 Contextual Retrieval generated summaries.
  2. M29 Postgres lexical retrieval and RRF.
  3. M30 Qwen sparse / `dense_sparse`.
  4. M31 Retrieval strategy gate.
- Keep dense retrieval as the default until M31 proves a promotion.
- Update progress/roadmap/docs so frontend polish follows retrieval capability
  stabilization.

## Out of Scope

- No runtime retrieval implementation in M27.
- No default promotion for contextual, lexical, sparse, graph or hybrid modes.
- No frontend polish.
- No Qwen sparse payload decisions without current provider documentation.
