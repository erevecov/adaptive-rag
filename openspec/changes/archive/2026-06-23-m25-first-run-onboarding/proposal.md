# Proposal M25 first-run onboarding

## Why

M23 and M24 expose public authoring and ingestion operations, but a new local
user still needs too much repo knowledge to reach a cited answer from their own
data. The first-run path must connect setup, migrations, sample/user content,
ingestion, indexing, chat and evidence without hidden fixtures or direct SQL.

## What Changes

- Add the `m25-first-run-onboarding` OpenSpec change.
- Add a public first-run CLI smoke that creates a project/source, runs
  ingestion, chunks and embeds the resulting document version, asks a cited
  question, and emits a JSON evidence report.
- Add a first-run runbook for local setup, migrations, default fake providers,
  public CLI commands and expected outputs.
- Refresh README/progress/roadmap so v1 next steps point to the final product
  quality gate.

## Out of Scope

- No hosted Qwen, rerank live, Neo4j, auth, PDF/Office, voice or MCP default.
- No frontend wizard; the current Authoring UI remains the product surface.
- No background worker management beyond documented local commands.
- No final v1 tag or release cut; that remains M26.
