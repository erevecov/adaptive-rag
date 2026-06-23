# Design M26 v1 product quality gate

## Context

The product now has public authoring, ingestion operations and a first-run
smoke. M26 should not add another product surface. It should provide the final
release gate that a reviewer can run locally and save as evidence before any
manual v1.0 tag decision.

## Approach

Add a CLI namespace `adaptive-rag v1` with a `quality-gate` command. The command
reuses `run_first_run_smoke()` and wraps its report in explicit v1 release
criteria:

1. Public first-run flow succeeded.
2. Ingestion job succeeded and exposed job state.
3. Chunking and dense fake embeddings produced indexed evidence.
4. Chat returned at least one citation.
5. The report includes next public commands for manual inspection.
6. Hosted providers, rerank live and Neo4j remain opt-in, not default gates.

The command is intentionally an evidence/reporting layer over the M25 product
flow. It does not create a tag, publish a release or promote any experimental
retrieval mode.

## Interfaces

- `adaptive-rag v1 quality-gate`
  - `--project-name`
  - `--source-external-id`
  - `--content`
  - `--question`
  - `--worker-id`
  - `--output`
- Output: JSON with `status`, `release_decision`, `criteria`, `first_run`,
  `deferred_defaults` and `manual_release_notes`.

## Error Handling

If the first-run smoke fails, the command exits non-zero with the underlying
stable first-run error. If the release criteria fail, it emits the report and
exits non-zero.

## Testing

Add CLI integration tests that first fail because the `v1 quality-gate` command
does not exist, then pass with an in-memory SQLite session and fake providers.
Add docs tests that assert the README and v1 quality-gate runbook document the
command, expected evidence fields, opt-in boundaries and manual tag boundary.
