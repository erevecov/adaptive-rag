# Delta spec de schema de dominio

## ADDED Requirements

### Requirement: Registros de proyecto definen aislamiento y modo de retrieval

El sistema MUST persistir registros de proyecto que aislen todos los datos RAG por `project_id` y definan configuracion de retrieval.

#### Scenario: Proyecto usa dense retrieval por defecto

- **WHEN** se crea un proyecto sin modo de embedding explicito
- **THEN** el `embedding_mode` guardado es `dense`
- **AND** `retrieval_contextualization_enabled` es `true`

#### Scenario: Configuracion de presupuesto del proyecto queda persistida

- **WHEN** un proyecto incluye configuracion de presupuesto
- **THEN** esa configuracion se guarda en `budget_config_json`

### Requirement: Sources y documents preservan identidad de ingestion

El sistema MUST persistir sources y documents con identificadores estables, source type, identificadores externos, metadata y pertenencia a proyecto.

#### Scenario: Documents pertenecen a un proyecto y source

- **WHEN** se crea un document desde un source
- **THEN** el document guarda `project_id` y `source_id`
- **AND** las queries de repository pueden filtrar por cualquiera de esos campos

#### Scenario: Metadata de source soporta filtering

- **WHEN** un source tiene tags, source type o metadata de fecha
- **THEN** esos valores se guardan en columnas tipadas o campos de metadata indexados aptos para filtering

### Requirement: Document versions anclan texto normalizado y citas

El sistema MUST guardar cada document version parseada con texto normalizado, parser metadata, extraction metadata, content hash e index fingerprint.

#### Scenario: Offsets de chunk refieren a texto normalizado

- **WHEN** se crea un chunk para una document version
- **THEN** `char_start` y `char_end` refieren a offsets en `document_versions.normalized_text`

#### Scenario: Re-indexing preserva document versions anteriores

- **WHEN** un document se re-parsea con texto normalizado o parser metadata distinta
- **THEN** se crea una fila nueva en `document_versions`
- **AND** los chunks existentes siguen apuntando a su version original

### Requirement: Chunks guardan inputs de embedding denso y limites semanticos

El sistema MUST persistir chunks con section metadata, conteo de tokens, enlaces vecinos, chunker metadata, campos reservados para contextual retrieval y embeddings densos.

#### Scenario: Columna de embedding denso tiene dimensiones compatibles con Qwen

- **WHEN** se migra el schema
- **THEN** `chunks.embedding` es una columna pgvector con 1024 dimensiones

#### Scenario: Lineage de chunks se puede reconstruir

- **WHEN** se recuperan chunks de una document version
- **THEN** `ordinal`, `prev_chunk_id` y `next_chunk_id` permiten reconstruir el orden local de chunks

### Requirement: Sparse embeddings son opcionales y aislados

El sistema MUST guardar datos de sparse embeddings en `chunk_sparse_embeddings` solo cuando un proyecto usa modo `dense_sparse`.

#### Scenario: Proyectos dense-only no necesitan filas sparse

- **WHEN** un proyecto usa `embedding_mode = dense`
- **THEN** retrieval puede operar sin filas en `chunk_sparse_embeddings`

#### Scenario: Filas sparse preservan metadata de reproducibilidad

- **WHEN** se guardan sparse embeddings
- **THEN** cada fila incluye sparse indices, sparse values, sparse tokens opcionales, sparse size, input hash e index fingerprint
