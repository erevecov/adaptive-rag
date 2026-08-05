# Propuesta Bloque C — Retrieval playground UI

## Why

Operators need to inspect ranked retrieval without going through chat.

## What Changes

- `apiClient.searchRetrieval` → `POST /projects/{id}/retrieval/search`
- Settings → Authoring → Retrieval playground panel
- Strategy / limit / optional rerank controls + results table
- Component tests

## Fuera de alcance

- Graph force-view, eval suites, memory UI
