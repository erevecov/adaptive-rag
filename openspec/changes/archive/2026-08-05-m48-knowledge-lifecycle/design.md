# Diseno M48 — Knowledge lifecycle

## Decisiones

1. **Sin migracion de columnas**: watermarks en `extra_metadata` (JSON) para
   evitar migracion en el stack tip; `content_hash` canonico sigue en
   `document_versions`.
2. **Resync = enqueue** del job publico `ingest_source` (no indexing inline).
3. **Dedup silencioso**: ingest ya reutiliza version por hash+fingerprint;
   el report solo observa grupos multi-version con el mismo hash.
4. **API** en authoring router (contributor para resync; access para status/report).

## Alternativas rechazadas

- Tabla `source_sync_state` separada (sobre-ingenieria para M48).
- Borrado automatico de duplicados (destructivo).
