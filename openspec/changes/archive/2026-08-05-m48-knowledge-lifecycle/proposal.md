# Propuesta M48 — Knowledge lifecycle (dedup + resync)

## Why

Tras indexacion publica (M40), no hay operacion de resync ni visibilidad de
estado de sync por fuente, ni reporte de documentos con el mismo content-hash.
Eso dificulta re-ingestar URLs actualizadas y detectar corpus duplicado.

## What Changes

- Watermark de sync en `sources.extra_metadata` (`last_content_hash`,
  `last_synced_at`) tras `ingest_source` exitoso.
- Resync CLI/API: re-encola `ingest_source` (path publico M40).
- Sync-status por fuente o proyecto.
- Dedup report: agrupa document versions por `content_hash` (sin delete).
- OpenSpec `knowledge-lifecycle`.

## Fuera de alcance

- Object store / blob de originales.
- Merge automatico o borrado de duplicados.
- M49 MCP, M50 reindex dense.
- Tag v1.0.

## Impacto

Operadores locales re-sincrizan fuentes y ven hashes/duplicados sin SQL ad-hoc.
