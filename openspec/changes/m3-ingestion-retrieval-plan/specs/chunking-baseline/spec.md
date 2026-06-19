## ADDED Requirements

### Requirement: Chunking baseline crea chunks desde document versions

El sistema MUST convertir `document_versions.normalized_text` en filas
`chunks` con offsets reproducibles, orden local y metadata de seccion/chunker.

#### Scenario: Document version Markdown crea chunks persistidos

- **WHEN** se chunkea una `document_version` de un proyecto
- **THEN** cada chunk guarda `char_start` y `char_end` relativos a
  `document_versions.normalized_text`
- **AND** los chunks tienen `ordinal` consecutivo desde cero
- **AND** los chunks guardan `section_metadata.section_path` y
  `section_metadata.heading`
- **AND** los chunks guardan `chunker_metadata.chunker_version =
  semantic_markdown_v1`
- **AND** no se guardan embeddings ni `contextual_summary`

#### Scenario: Lineage de chunks queda persistido

- **WHEN** el baseline crea mas de un chunk para una document version
- **THEN** cada chunk intermedio enlaza `prev_chunk_id` y `next_chunk_id`
- **AND** el primer chunk no tiene `prev_chunk_id`
- **AND** el ultimo chunk no tiene `next_chunk_id`

### Requirement: Chunking baseline preserva reconstruccion por offsets

El sistema MUST crear spans que permitan reconstruir el texto normalizado
original leyendo chunks por `ordinal`, ignorando solo overlap explicito cuando
la configuracion lo active.

#### Scenario: Reconstruccion sin overlap reproduce el texto original

- **WHEN** el chunker corre con `overlap_tokens = 0`
- **THEN** concatenar `normalized_text[char_start:char_end]` en orden de
  `ordinal` reproduce exactamente `document_versions.normalized_text`

#### Scenario: Overlap explicito mantiene reconstruccion sin duplicados

- **WHEN** el chunker corre con `overlap_tokens > 0`
- **THEN** los chunks vecinos pueden tener rangos `char_start`/`char_end`
  solapados
- **AND** reconstruir el texto ignorando el prefijo duplicado de cada chunk
  reproduce `document_versions.normalized_text`

#### Scenario: Bloque sobredimensionado usa fallback por tokens

- **WHEN** un bloque estructural excede `max_chunk_tokens`
- **THEN** el chunker divide ese bloque con fallback deterministico por tokens
- **AND** los offsets resultantes siguen cubriendo el texto original en orden

### Requirement: Chunking baseline mantiene aislamiento e idempotency

El sistema MUST exigir `project_id` al persistir chunks y MUST reutilizar chunks
existentes cuando una document version ya fue chunkeada con la misma
configuracion.

#### Scenario: Document version de otro proyecto se rechaza

- **WHEN** se solicita chunking con un `project_id` que no contiene la
  `document_version`
- **THEN** el sistema no crea chunks
- **AND** devuelve un error estable de pertenencia de proyecto

#### Scenario: Segunda corrida con misma configuracion reutiliza chunks

- **WHEN** se ejecuta el chunking dos veces sobre la misma document version
- **AND** la configuracion del chunker no cambio
- **THEN** la segunda corrida devuelve los chunks existentes
- **AND** no crea chunks duplicados
