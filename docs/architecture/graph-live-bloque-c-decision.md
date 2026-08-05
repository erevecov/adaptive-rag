# Bloque C — Graph live evidence decision (2026-08-05)

**Status:** `hold` (documented decision; not a product default)

## Context

Marathon Bloque A+B (M40–M50) is implemented on stacked PRs with tip
`feat/m50-dense-reindex`. Graph remains in quality-gate `deferred_defaults`
as `neo4j_graph`.

## Decision

Do **not** promote graph retrieval to default in this marathon closeout.

| Option | Choice |
|--------|--------|
| Ship graph live evidence + force-graph UI | Deferred |
| Documented `no_go` | Not selected — graph stays **opt-in/hold** |
| Hold with existing projection/fallback | **Selected** |

## Rationale

1. Graph path already has dense fallback when projection is not `ready` (M47 router respects `graph_ready`).
2. Live Neo4j ops evidence remains environment-dependent; local-first default must not require Neo4j.
3. Marathon anti-roadmap forbids expanding GraphRAG complexity; keep projection reconstruible, not community GraphRAG.

## Residual / next (human)

- Optional: re-run Neo4j live harness when a Neo4j instance is available and attach evidence under `docs/architecture/graph-live-evidence-report-m19.md` successors.
- Until then: `neo4j_graph` stays deferred; routing uses `dense_sparse` when not ready.

## Explicit non-actions

- No v1.0 tag from this decision
- No SaaS multi-tenant / Redis / SPLADE
