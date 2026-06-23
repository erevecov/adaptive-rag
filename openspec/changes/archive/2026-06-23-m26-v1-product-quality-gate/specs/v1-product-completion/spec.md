## ADDED Requirements

### Requirement: V1 product completion includes final quality gate

The product-completion gate MUST include a final public command that produces
release evidence from the complete local-first product flow.

#### Scenario: Quality gate proves final product flow

- **WHEN** a reviewer runs `adaptive-rag v1 quality-gate` against an initialized
  local database
- **THEN** the command creates user/sample data through public product services
- **AND** it runs ingestion, chunking, embeddings and cited chat through the
  default local path
- **AND** it emits a machine-readable report with release criteria, first-run
  evidence, job state, indexing counts, citation count and release decision

#### Scenario: Quality gate keeps optional systems out of default release

- **WHEN** the v1 quality gate reports release evidence
- **THEN** hosted Qwen, hosted rerank and Neo4j remain marked opt-in
- **AND** auth multi-user, PDF/Office, voice, MCP server and hosted
  observability remain explicit deferrals
- **AND** dense retrieval remains the default path for v1.0
