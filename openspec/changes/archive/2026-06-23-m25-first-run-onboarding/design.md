# Design M25 first-run onboarding

## Context

The product can now create projects/sources and operate ingestion jobs from API,
CLI and frontend. The missing product step is a reproducible first run that a
reviewer can execute from a clean local environment to prove the public flow.

## Approach

Add a CLI namespace `adaptive-rag first-run` with a `smoke` command. The command
uses existing public/domain services in one local transaction sequence:

1. Create a project with dense defaults.
2. Create a Markdown source from supplied content or a built-in sample.
3. Enqueue and run one `ingest_source` job.
4. Chunk and embed the resulting document version with the existing default fake
   provider path.
5. Ask a chat question through `ChatService` and print a JSON report.

The command is intentionally a first-run smoke, not a general indexing API. It
uses reusable internal pipelines because the v1 default path needs an executable
proof now, while broader indexing/admin surfaces can remain out of M25.

## Interfaces

- `adaptive-rag first-run smoke`
  - `--project-name`
  - `--source-external-id`
  - `--content`
  - `--question`
  - `--worker-id`
- Output: JSON with `status`, created ids, job status, chunk/embed counts,
  answer, citation count and next recommended commands.
- Docs: `docs/first-run.md` plus README links and post-M25 progress/roadmap.

## Error Handling

The command exits non-zero with a stable stderr message when ingestion blocks,
chunking fails, embedding fails or chat returns no citations. The default fake
provider path must not require hosted credentials.

## Testing

Add CLI integration tests that watch `first-run smoke` fail before the command
exists, then pass with an in-memory SQLite session and fake providers. Add docs
tests that assert README and first-run runbook mention the required command
sequence and opt-in provider boundaries.
