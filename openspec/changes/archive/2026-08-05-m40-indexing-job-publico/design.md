# Diseno M40 — indexing job publico

## Contexto

- `IngestionPipeline` procesa `ingest_source` → `document_versions` y no crea
  chunks ni embeddings (correcto para el slice M3).
- `ChunkingPipeline`, `ContextualizationPipeline`, `DenseEmbeddingPipeline` y
  `SparseEmbeddingPipeline` ya existen y son idempotentes.
- first-run / acceptance / quality-gate hoy llaman esas pipelines inline tras
  un unico `run_next` de ingest.

## Decisiones

### 1. Un job `index_document_version` (no N jobs micro)

Payload:

```json
{
  "document_version_id": "<uuid>",
  "source_id": "<uuid>"
}
```

El job ejecuta en orden: chunk → contextualize → dense embed → sparse embed.
Un solo job es mas simple de observar, reintentar y de drenar en first-run.
Micro-jobs por etapa quedan fuera de M40 (se pueden dividir en M50 si hace falta
reindex selectivo).

### 2. Encadenado al completar `ingest_source`

Tras `complete` de un `ingest_source` exitoso, el pipeline encola un
`index_document_version` para la document version resultante (creada o
reutilizada). Enqueue no indexa; solo el worker lo hace.

### 3. Worker family de ingestion

`run_next` / `run-worker` leasan el siguiente job entre
`{ingest_source, index_document_version}` (prioridad/run_after existentes).
Jobs de graph u otros tipos no se tocan.

### 4. Providers inyectables + runtime resolution

`IndexingPipeline` acepta dense/sparse/contextualizer opcionales (tests y
first-run fake). Si no se inyectan, resuelve via factories de runtime por
`project_id` (mismo path que acceptance post-settings).

### 5. Gates usan el path de jobs

first-run / acceptance / quality-gate:

1. authoring create project/source
2. enqueue `ingest_source`
3. loop `run_next` hasta idle (procesa ingest + index)
4. chat con retrieval + citations

No llaman `ChunkingPipeline` / embed pipelines directamente.

## Alternativas rechazadas

- **Expandir `ingest_source` para indexar inline:** pierde observabilidad de
  etapas y mezcla parsing con providers costosos en el mismo job.
- **Solo API de indexing sin job:** no es el path de worker/producto.
- **N jobs (chunk, embed, …):** mas superficie de retry y ordering sin beneficio
  en M40.

## Riesgos

- Tests que asumen que `run_next` una sola vez deja el corpus listo: actualizar a
  drain hasta idle o dos run-next.
- Spec historica "pipeline no crea chunks" se mantiene para `ingest_source`; se
  agrega requirement de enqueue de indexing.
