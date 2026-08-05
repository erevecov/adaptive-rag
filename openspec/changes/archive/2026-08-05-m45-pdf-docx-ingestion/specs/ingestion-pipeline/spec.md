## MODIFIED Requirements

### Requirement: URL ingestion usa fetch seguro antes del extractor HTML

El sistema MUST usar `URLFetcher` o un adapter compatible para descargar
sources `url` antes de parsear. Tras el fetch, el pipeline MUST seleccionar el
parser registrado segun el content-type base de la respuesta:

- `text/html` y `application/xhtml+xml` → extractor HTML (Trafilatura o
  equivalente)
- `application/pdf` → parser PDF de texto embebido
- `application/vnd.openxmlformats-officedocument.wordprocessingml.document` →
  parser DOCX

Content-types allowlisted en fetch pero sin parser registrado MUST bloquear el
job sin llamar al extractor HTML.

#### Scenario: Source URL usa resultado del fetcher

- **WHEN** un job `ingest_source` procesa una source `url`
- **AND** el fetcher devuelve content-type HTML o XHTML
- **THEN** el pipeline llama al fetcher con `source.external_id`
- **AND** pasa el HTML descargado y la URL final al extractor HTML
- **AND** persiste el texto normalizado en `document_versions.normalized_text`

#### Scenario: Source URL PDF extrae texto embebido

- **WHEN** un job `ingest_source` procesa una source `url`
- **AND** el fetcher devuelve `application/pdf` con texto embebido
- **THEN** el pipeline no llama al extractor HTML
- **AND** extrae texto con el parser PDF registrado
- **AND** crea o reutiliza una document version con texto normalizado no vacio
- **AND** registra `parser_metadata` con id/version del parser PDF
- **AND** marca el job como `succeeded`
- **AND** encola `index_document_version` (contrato M40)

#### Scenario: Source URL no HTML bloquea el job

- **WHEN** un job `ingest_source` procesa una source `url`
- **AND** el fetcher devuelve un content-type allowlisted sin parser
  registrado (por ejemplo `text/plain`) o un tipo que el registry no soporta
- **THEN** el pipeline no llama al extractor HTML
- **AND** marca el job como `blocked`
- **AND** no crea document versions

#### Scenario: Source URL con content-type sin parser bloquea el job

- **WHEN** un job `ingest_source` procesa una source `url`
- **AND** el fetcher devuelve un content-type allowlisted sin parser
  (por ejemplo `text/plain` si no hay parser de plain URL) o un tipo que el
  registry no soporta para parse
- **THEN** el pipeline no llama al extractor HTML
- **AND** marca el job como `blocked`
- **AND** no crea document versions

## ADDED Requirements

### Requirement: PDF sources extract embedded text into document versions

El sistema MUST parsear sources de tipo `pdf` (payload binario en
`extra_metadata.content_base64`) y respuestas URL `application/pdf` usando un
parser de **texto embebido** (sin OCR). El resultado MUST ser
`document_versions.normalized_text` con `parser_metadata` e
`index_fingerprint` como el resto de sources.

#### Scenario: PDF tipado con texto embebido crea document version

- **WHEN** un job `ingest_source` procesa una source `pdf` con
  `extra_metadata.content_base64` que decodifica a un PDF con texto embebido
- **THEN** el pipeline crea o reutiliza una document version con texto
  normalizado no vacio
- **AND** `parser_metadata` incluye el parser PDF y su version
- **AND** el job queda `succeeded`
- **AND** se encola indexing por separado (sin chunks en el job de ingest)

#### Scenario: PDF sin texto embebido bloquea sin OCR

- **WHEN** el parser PDF no produce texto usable (strip vacio)
- **THEN** el job se marca `blocked` con un error estable de extraccion vacia
- **AND** el sistema no invoca OCR ni vision
- **AND** no se indexa un corpus vacio como exito

### Requirement: DOCX sources extract document text into document versions

El sistema MUST parsear sources de tipo `docx` (payload
`extra_metadata.content_base64`) y respuestas URL con content-type DOCX OOXML
produciendo texto normalizado y metadata de parser.

#### Scenario: DOCX tipado crea document version

- **WHEN** un job `ingest_source` procesa una source `docx` con body text
- **THEN** se persiste `normalized_text` no vacio
- **AND** el job queda `succeeded`
- **AND** se encola `index_document_version` por separado

#### Scenario: DOCX sin texto bloquea

- **WHEN** el parser DOCX no produce texto usable
- **THEN** el job se marca `blocked` con error estable de extraccion vacia

### Requirement: Document parser registry selects parser by type

El sistema MUST enrutar ingest mediante un registry (mapa o equivalente) de
`source_type` y/o content-type hacia parsers concretos, de modo que
markdown/text, HTML URL, PDF y DOCX no dependan de un unico branch opaco sin
extension points.

#### Scenario: Source type no soportado sigue bloqueado

- **WHEN** un job referencia un `source_type` fuera del conjunto soportado
- **THEN** el job se marca `blocked`
- **AND** no se crean document versions

#### Scenario: content_base64 invalido o ausente en pdf/docx bloquea

- **WHEN** una source `pdf` o `docx` no tiene `content_base64` decodificable
- **THEN** el job se marca `blocked` con error estable
- **AND** no se crean document versions
