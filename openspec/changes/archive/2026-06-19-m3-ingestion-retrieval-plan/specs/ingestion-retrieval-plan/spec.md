## ADDED Requirements

### Requirement: M3 se entrega en slices secuenciales

El sistema MUST planificar M3 como slices secuenciales que separen ingestion,
chunking, embeddings y retrieval.

#### Scenario: Ingestion precede chunking y retrieval

- **WHEN** se inicia M3 despues de cerrar M2
- **THEN** el primer slice de implementacion es `m3-ingestion-pipeline`
- **AND** no implementa chunking, embeddings ni retrieval

#### Scenario: Chunking precede embeddings y retrieval

- **WHEN** `m3-ingestion-pipeline` queda mergeado
- **THEN** el siguiente slice implementa `m3-chunking-baseline`
- **AND** valida offsets y reconstruccion de texto antes de persistir embeddings

#### Scenario: Embeddings preceden retrieval

- **WHEN** `m3-chunking-baseline` queda mergeado
- **THEN** el siguiente slice implementa `m3-embedding-baseline`
- **AND** usa fakes deterministas antes de requerir providers live

### Requirement: M3 conserva aislamiento por proyecto desde el primer slice

El sistema MUST mantener `project_id` como frontera obligatoria en ingestion,
chunking, embeddings y retrieval.

#### Scenario: Jobs de ingestion no cruzan proyectos

- **WHEN** un worker reclama un job `ingest_source`
- **THEN** carga source, document y document version usando el mismo `project_id`
- **AND** registra eventos del job con ese `project_id`

#### Scenario: Retrieval filtra antes de rankear

- **WHEN** un retrieval query se ejecuta en M3
- **THEN** aplica `project_id` y filtros tipados antes de ordenar candidatos
- **AND** no devuelve chunks de otro proyecto

### Requirement: M3 prioriza contratos deterministas antes de providers live

El sistema MUST validar parsing, chunking, embeddings y retrieval con fakes o
datos deterministas antes de depender de credenciales o red de providers.

#### Scenario: Embedding baseline usa fake provider

- **WHEN** se implementa `m3-embedding-baseline`
- **THEN** los tests principales usan un provider fake que devuelve vectores de
  1024 dimensiones
- **AND** el codigo valida la dimension antes de persistir el embedding

#### Scenario: Provider live queda opt-in

- **WHEN** faltan credenciales de Qwen u otro provider hosted
- **THEN** los tests obligatorios de M3 siguen corriendo con fakes
- **AND** cualquier smoke live queda documentado como opt-in

### Requirement: Citations se anclan al texto normalizado original

El sistema MUST preservar citations sobre `document_versions.normalized_text` y
chunks originales, no sobre texto contextual generado.

#### Scenario: Chunk guarda offsets reproducibles

- **WHEN** el chunker crea chunks para una document version
- **THEN** cada chunk guarda `char_start` y `char_end` relativos a
  `document_versions.normalized_text`
- **AND** `text` no incluye `contextual_text`

#### Scenario: Citation usa texto original

- **WHEN** retrieval retorna un chunk como evidencia
- **THEN** el payload de citation referencia source, document, chunk, offsets y
  snippet del texto original
- **AND** no usa el contexto generado como evidencia factual visible

