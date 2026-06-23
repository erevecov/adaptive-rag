# embedding-baseline Specification

## Purpose

Definir la frontera inicial de embeddings densos, incluyendo construccion de
inputs, provider fake determinista, metadata reproducible, validacion de
dimension e idempotency por chunk.
## Requirements
### Requirement: Embedding baseline construye inputs desde chunks

El sistema MUST construir `embedding_input_text` y `lexical_input_text` desde
chunks persistidos y el texto normalizado original de la document version.

#### Scenario: Chunk sin contexto usa texto original

- **WHEN** un chunk no tiene `contextual_summary`
- **THEN** `embedding_input_text` es el slice
  `document_versions.normalized_text[char_start:char_end]`
- **AND** `lexical_input_text` usa el mismo texto en este baseline

#### Scenario: Chunk contextualizado antepone resumen

- **WHEN** un chunk tiene `contextual_summary`
- **THEN** `embedding_input_text` antepone ese contexto al texto original del
  chunk
- **AND** el texto original sigue siendo el slice de
  `document_versions.normalized_text`

### Requirement: Embedding baseline persiste embeddings densos con fakes

El sistema MUST usar una interfaz pequena de provider de embeddings densos y
MUST permitir un fake determinista de 1024 dimensiones para tests obligatorios.

#### Scenario: Fake provider persiste embedding y metadata

- **WHEN** el pipeline de embeddings procesa chunks de una document version
- **THEN** llama al provider fake con los `embedding_input_text`
- **AND** persiste vectores densos en `chunks.embedding`
- **AND** persiste metadata reproducible en `chunks.embedding_metadata`
- **AND** no crea sparse embeddings ni ejecuta retrieval

#### Scenario: Dimension incorrecta bloquea persistencia

- **WHEN** el provider devuelve embeddings con una dimension distinta de 1024
- **THEN** el pipeline devuelve un error estable de dimension
- **AND** no persiste embeddings parciales

### Requirement: Embedding baseline mantiene aislamiento e idempotency

El sistema MUST exigir `project_id` al persistir embeddings y MUST reutilizar
embeddings existentes cuando provider, modelo, dimension e input hash no
cambian.

#### Scenario: Document version de otro proyecto se rechaza

- **WHEN** se solicita embedding con un `project_id` que no contiene la
  `document_version`
- **THEN** el sistema no llama al provider
- **AND** no persiste embeddings

#### Scenario: Segunda corrida reutiliza embeddings existentes

- **WHEN** se ejecuta embeddings dos veces con el mismo provider, modelo,
  dimension e input hash
- **THEN** la segunda corrida reutiliza los embeddings existentes
- **AND** no llama de nuevo al provider para esos chunks

### Requirement: Contextual summaries are generated before embedding

The system MUST provide a project-scoped contextualization pipeline that fills
`chunks.contextual_summary` before dense embeddings are generated.

#### Scenario: Pipeline fills missing summaries

- **WHEN** a document version has chunks without `contextual_summary`
- **THEN** the contextualization pipeline generates one bounded summary per
  chunk
- **AND** persists it on `chunks.contextual_summary`
- **AND** preserves the original chunk offsets and normalized document text

#### Scenario: Pipeline reuses existing summaries

- **WHEN** a chunk already has a non-empty `contextual_summary`
- **THEN** the contextualization pipeline reuses it
- **AND** does not regenerate or overwrite the field

#### Scenario: Cross-project versions are rejected

- **WHEN** contextualization is requested with a `project_id` that does not own
  the document version
- **THEN** the system returns a stable error
- **AND** no chunks are updated

#### Scenario: Generated context drives embedding inputs

- **WHEN** dense embedding runs after contextualization
- **THEN** generated summaries are included in the embedding and lexical inputs
- **AND** embedding metadata records the contextualized input kind and hashes
