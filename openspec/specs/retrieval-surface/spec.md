# retrieval-surface Specification

## Purpose

Definir la primera superficie publica de retrieval sobre el baseline M3,
incluyendo el servicio compartido para API/CLI, query embeddings mediante
provider inyectado, filtros tipados y resultados serializables con citations.
## Requirements
### Requirement: Retrieval surface usa un servicio compartido

El sistema MUST exponer retrieval mediante un servicio compartido que recibe
query text, genera query embedding con un provider inyectado y llama al dense
retriever baseline.

#### Scenario: Query text ejecuta dense retrieval

- **WHEN** una solicitud de retrieval incluye `project_id`, `query` y `limit`
- **THEN** el servicio genera un query embedding con el provider configurado
- **AND** llama a `DenseRetriever` con ese embedding
- **AND** retorna resultados con score y citation payload

#### Scenario: Provider fake permite tests deterministas

- **WHEN** los tests ejecutan retrieval surface sin credenciales live
- **THEN** usan un provider fake determinista
- **AND** no llaman a red ni providers hosted

### Requirement: Retrieval surface aplica filtros tipados

El sistema MUST aceptar filtros tipados compatibles con el baseline M3 y MUST
rechazar filtros desconocidos en la superficie API.

#### Scenario: Filtros externos se aplican antes de rankear

- **WHEN** una solicitud incluye `source_id`, `document_id`, `source_type`,
  `tags` o rangos de fecha soportados
- **THEN** el servicio mapea esos filtros a `DenseRetrievalFilters`
- **AND** no devuelve chunks que no cumplan los filtros

#### Scenario: Campo de filtro desconocido se rechaza

- **WHEN** la API recibe un `metadata_filter` con campos no soportados
- **THEN** responde con un error de validacion
- **AND** no ejecuta retrieval

### Requirement: Retrieval surface publica API y CLI minimas

El sistema MUST proveer un endpoint FastAPI y un comando Typer que usen el
mismo servicio de retrieval.

#### Scenario: API retorna results con citations

- **WHEN** `POST /projects/{project_id}/retrieval/search` recibe una solicitud
  valida
- **THEN** retorna results serializables con `chunk_id`, score y citation
- **AND** no implementa chat/tool calling

#### Scenario: CLI usa los mismos filtros que la API

- **WHEN** `adaptive-rag retrieval search` recibe query, limit y filtros
- **THEN** llama al mismo servicio que la API
- **AND** emite una salida estable para tests automatizados

### Requirement: Retrieval surface exposes lexical and hybrid RRF strategies

The system MUST expose local lexical retrieval and hybrid dense+lexical RRF as
explicit retrieval strategies without changing the dense_sparse default.

#### Scenario: Lexical strategy returns original citations

- **WHEN** retrieval is requested with `strategy=lexical`
- **THEN** the system ranks chunks by lexical match against contextualized
  lexical input
- **AND** returns result payloads with `strategy` equal to `lexical`
- **AND** citation snippets are sourced from original normalized document text

#### Scenario: Hybrid RRF fuses dense and lexical candidates

- **WHEN** retrieval is requested with `strategy=hybrid_rrf`
- **THEN** the system runs dense and lexical candidate lists after applying
  project and metadata filters
- **AND** fuses candidate ranks with reciprocal rank fusion
- **AND** emits at most one result per chunk with stable ordering

#### Scenario: dense_sparse remains default

- **WHEN** no retrieval strategy is supplied by API, CLI, chat or eval callers
- **THEN** the system uses `dense_sparse`
- **AND** lexical and hybrid RRF never run implicitly

#### Scenario: Result metadata preserves strategy scores

- **WHEN** lexical or hybrid RRF returns results
- **THEN** result payloads include score metadata for the active strategy
- **AND** existing rerank metadata remains available when rerank is explicitly
  requested

### Requirement: Retrieval surface exposes local Okapi BM25 strategy

The system MUST expose `strategy=bm25` as a local, provider-free retrieval
strategy over the contextualized lexical input without changing the dense_sparse
default.

#### Scenario: BM25 strategy returns original citations

- **WHEN** retrieval is requested with `strategy=bm25`
- **THEN** the system scores filtered chunks with Okapi BM25 locally
- **AND** returns result payloads with `strategy` equal to `bm25`
- **AND** result metadata records BM25 rank and score
- **AND** citation snippets are sourced from original normalized document text

#### Scenario: BM25 does not call embedding providers

- **WHEN** retrieval is requested with `strategy=bm25`
- **THEN** no dense or sparse embedding provider is required or called
- **AND** project and metadata filters are applied before scoring

### Requirement: Retrieval surface exposes sparse and dense_sparse strategies

The system MUST expose `strategy=sparse` and `strategy=dense_sparse` for API,
CLI, chat and offline evals, with `dense_sparse` as the default retrieval
strategy.

#### Scenario: Sparse strategy returns original citations

- **WHEN** retrieval is requested with `strategy=sparse`
- **THEN** the service embeds the query with the configured sparse provider
- **AND** ranks stored sparse embeddings after applying project and metadata
  filters
- **AND** returns result payloads with `strategy` equal to `sparse`
- **AND** records sparse rank and score in result metadata

#### Scenario: dense_sparse fuses dense and sparse candidates

- **WHEN** retrieval is requested with `strategy=dense_sparse`
- **THEN** the service runs dense retrieval and sparse retrieval over the same
  query, project and filters
- **AND** deduplicates candidates by chunk id
- **AND** applies reciprocal rank fusion
- **AND** records dense rank, sparse rank and RRF score in result metadata

#### Scenario: dense_sparse remains default

- **WHEN** no retrieval strategy is supplied by API, CLI, chat or eval callers
- **THEN** retrieval uses `strategy=dense_sparse`
- **AND** dense and sparse retrieval run implicitly through the configured
  providers

#### Scenario: dense remains available explicitly

- **WHEN** retrieval is requested with `strategy=dense`
- **THEN** retrieval uses only the dense embedding provider and dense index
- **AND** sparse retrieval does not run

#### Scenario: Sparse backfill is explicit

- **WHEN** a user wants sparse retrieval coverage for a project
- **THEN** they run an explicit sparse backfill command for that project
- **AND** the command reports embedded, reused and total chunk counts
