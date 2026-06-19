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
