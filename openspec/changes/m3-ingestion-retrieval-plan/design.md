# Diseno M3 de ingestion y retrieval

## Contexto

M2 dejo cuatro contratos listos: `domain-schema`, `repositories`, `job-queue` y
`url-fetch-policy`. M3 debe usar esos contratos para construir un vertical
slice de ingestion y retrieval sin romper aislamiento por `project_id`, sin
perder offsets reproducibles para citations y sin acoplar el dominio a
providers live desde el primer PR.

## Enfoques considerados

### A. PR unico de ingestion a retrieval completo

Un solo PR conectaria Source, jobs, parsing, chunking, embeddings y retrieval.
Es rapido en apariencia, pero mezcla seguridad, persistencia, provider
boundaries y ranking. No es recomendable porque cualquier fallo obliga a
revisar todo junto.

### B. Slices secuenciales por frontera estable

Cada PR entrega una frontera verificable: ingestion normaliza texto,
chunking crea offsets, embeddings persisten vectores via fakes y retrieval
consulta esos datos con filtros. Es la opcion recomendada porque reduce
conflictos, permite TDD por contrato y mantiene providers live fuera hasta que
la persistencia sea determinista.

### C. Retrieval-first sobre fixtures manuales

Implementar retrieval antes de ingestion permite validar ranking temprano, pero
pospone offsets, document versions e index fingerprints. No es recomendable
como primer corte porque retrieval necesita datos creados con las mismas reglas
que luego usara ingestion.

## Decision

Usar el enfoque B: slices secuenciales por frontera estable.

## Secuencia de M3

### 1. `m3-ingestion-pipeline`

Conectar `SourceRepository`, `DocumentRepository`, `JobRepository` y
`URLFetchPolicy` para convertir una source en una `document_version` con texto
normalizado, metadata de parser, hash e `index_fingerprint`.

Alcance:

- URL HTML publica con `URLFetcher` y extractor HTML fake/trafilatura wrapper.
- Markdown/TXT con parser basico determinista.
- Job `ingest_source` con eventos de auditoria.
- Persistencia de `document_versions`.

Fuera de alcance:

- Chunking.
- Embeddings.
- Provider calls live.
- Retrieval.

### 2. `m3-chunking-baseline`

Implementar el chunker determinista `semantic_markdown_v1` sobre
`document_versions.normalized_text`.

Alcance:

- `TokenEstimator` local.
- Chunking por estructura primero y tokens como fallback.
- `char_start`, `char_end`, `ordinal`, `prev_chunk_id`, `next_chunk_id`,
  `section_path`, `heading`, `token_count`, `chunker_version` y
  `chunker_config_hash`.
- Tests de reconstruccion de texto normalizado ignorando overlap explicito.

Fuera de alcance:

- Contextual Retrieval con Qwen.
- Embeddings.
- Retrieval API/CLI.

### 3. `m3-embedding-baseline`

Definir la frontera de embeddings y persistir embeddings densos con fakes
deterministas antes de integrar providers live.

Alcance:

- Construccion de `embedding_input_text` y `lexical_input_text`.
- Interfaz pequena de embedding provider.
- Fake provider que devuelve vectores de dimension 1024 para tests.
- Persistencia de metadata de embedding dense en chunks.
- Validacion de dimension.

Fuera de alcance:

- Qwen live obligatorio.
- Sparse embeddings.
- Rerank.
- Cost tracking completo.

### 4. `m3-retrieval-baseline`

Implementar retrieval exacto inicial sobre datos persistidos.

Alcance:

- Dense retrieval exacto con pgvector como baseline de correctness.
- Filtro obligatorio por `project_id`.
- Filtros por `source_id`, `document_id`, `source_type`, `tags` y rangos de
  fecha cuando las columnas M2 ya los soporten.
- Payload de citation basado en texto original, offsets y metadata de source.
- Tests de aislamiento cross-project.

Fuera de alcance:

- Lexical full-text, RRF, Qwen sparse, Qwen rerank y chat tool calling.
- HNSW.
- API/CLI extensa mas alla del contrato minimo que el slice apruebe.

### 5. `m3-quality-gate`

Cerrar M3 cuando los slices anteriores esten mergeados, validando specs,
tests, lint, types y docs.

## Riesgos y mitigaciones

- Riesgo: implementar provider live antes de tener persistencia estable.
  Mitigacion: `m3-embedding-baseline` empieza con fakes y dimension checks.
- Riesgo: offsets de citations invalidos por chunking temprano.
  Mitigacion: `m3-chunking-baseline` bloquea embeddings/retrieval hasta tener
  tests de offsets y reconstruccion.
- Riesgo: retrieval mezcla filtros tarde.
  Mitigacion: `m3-retrieval-baseline` exige aislamiento por `project_id` y
  filtros antes de ranking.
- Riesgo: roadmap quede como docs sueltos.
  Mitigacion: este change queda activo en OpenSpec y las tareas se actualizan
  por PR secuencial.

## Validacion esperada por slice

Cada slice debe ejecutar:

```text
uv run pytest
uv run ruff check .
uv run mypy src
openspec validate <change-id> --strict
openspec validate --specs --strict
```

Los slices que toquen DB deben incluir tests unitarios y, cuando aplique,
tests de integracion con Postgres/pgvector via testcontainers.

