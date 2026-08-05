# mcp-server Specification

## Purpose

Definir el servidor MCP stdio minimo de Adaptive RAG para integracion local
con Claude Code / Cursor, reutilizando el camino publico de producto.

## Requirements

### Requirement: MCP stdio server exposes product tools

The system MUST provide an MCP stdio server with tools
`list_projects`, `list_sources`, `search`, `ask`, and `ingest_text` that
delegate to the same authoring/retrieval/chat/ingestion job paths as CLI/API.

#### Scenario: Required tool names are registered

- **WHEN** the MCP server is built
- **THEN** it exposes exactly the five required tools by name

#### Scenario: ingest_text enqueues public ingest job

- **WHEN** `ingest_text` is invoked with project id, external id and content
- **THEN** a markdown source is created
- **AND** an `ingest_source` job is enqueued for that source

#### Scenario: list_projects returns project payloads

- **WHEN** `list_projects` is invoked
- **THEN** it returns a JSON list of projects from the local database

### Requirement: MCP entry is available via CLI

The system MUST expose `adaptive-rag mcp serve` to run the stdio server.

#### Scenario: CLI registers mcp command

- **WHEN** the root CLI app is inspected
- **THEN** an `mcp` command group with `serve` is registered
