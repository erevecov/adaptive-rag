# ingestion-pipeline Specification

## Purpose

Definir el pipeline inicial que procesa jobs `ingest_source` y convierte
sources soportadas en `document_versions` normalizadas, auditables e
idempotentes dentro de un proyecto.
## Requirements
### Requirement: Ingestion pipeline convierte sources en document versions

El sistema MUST procesar jobs `ingest_source` para convertir sources de un
proyecto en `document_versions` con texto normalizado, hash de contenido,
metadata de parser e `index_fingerprint`.

#### Scenario: Source Markdown crea primera document version

- **WHEN** un job `ingest_source` referencia una source Markdown del mismo
  proyecto
- **THEN** el pipeline crea o reutiliza el document asociado a esa source
- **AND** crea `document_versions.version_number = 1`
- **AND** normaliza line endings del texto fuente
- **AND** marca el job como `succeeded`

#### Scenario: Reingestion idempotente reutiliza version existente

- **WHEN** se procesa otra vez la misma source con el mismo contenido y parser
- **THEN** el pipeline reutiliza la document version existente
- **AND** no crea una version duplicada
- **AND** marca el job nuevo como `succeeded`

### Requirement: Ingestion pipeline mantiene aislamiento por proyecto

El sistema MUST rechazar jobs `ingest_source` cuyo payload intente cargar una
source que no pertenece al `project_id` del job leaseado.

#### Scenario: Source de otro proyecto bloquea el job

- **WHEN** un job de un proyecto referencia una source de otro proyecto
- **THEN** el pipeline no crea documents ni document versions
- **AND** marca el job como `blocked`
- **AND** registra el evento `blocked` con el mismo `project_id` del job

### Requirement: URL ingestion usa fetch seguro antes del extractor HTML

El sistema MUST usar `URLFetcher` o un adapter compatible para descargar sources
`url` antes de pasar HTML ya descargado al extractor. El pipeline MUST pasar al
extractor solo respuestas con content type base `text/html` o
`application/xhtml+xml`.

#### Scenario: Source URL usa resultado del fetcher

- **WHEN** un job `ingest_source` procesa una source `url`
- **THEN** el pipeline llama al fetcher con `source.external_id`
- **AND** pasa el HTML descargado y la URL final al extractor HTML
- **AND** persiste el texto normalizado devuelto por el extractor en
  `document_versions.normalized_text`

#### Scenario: Source URL no HTML bloquea el job

- **WHEN** un job `ingest_source` procesa una source `url`
- **AND** el fetcher devuelve un content type distinto de HTML o XHTML
- **THEN** el pipeline no llama al extractor HTML
- **AND** marca el job como `blocked`

### Requirement: Ingestion pipeline no implementa chunking ni embeddings

El sistema MUST mantener `m3-ingestion-pipeline` limitado a parsing y
persistencia de `document_versions`.

#### Scenario: Pipeline no crea chunks

- **WHEN** un job `ingest_source` termina exitosamente en este slice
- **THEN** no se crean chunks
- **AND** no se llaman providers de embeddings
