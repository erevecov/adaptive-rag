## MODIFIED Requirements

### Requirement: Content type y tamano de respuesta son limitados

El sistema MUST limitar los content types y el tamano de bytes descargados.
La allowlist MUST incluir al menos:

- `text/html`
- `application/xhtml+xml`
- `text/plain`
- `application/pdf`
- `application/vnd.openxmlformats-officedocument.wordprocessingml.document`

#### Scenario: Content type no permitido se rechaza

- **WHEN** una respuesta final tiene `Content-Type` fuera de la allowlist
- **THEN** el fetcher rechaza la respuesta antes de consumir el cuerpo

#### Scenario: Content-Length excede el limite

- **WHEN** una respuesta final declara `Content-Length` mayor que
  `max_response_bytes`
- **THEN** el fetcher rechaza la respuesta antes de consumir el cuerpo

#### Scenario: Stream excede el limite

- **WHEN** una respuesta sin `Content-Length` excede `max_response_bytes`
  mientras se lee
- **THEN** el fetcher detiene la lectura y falla con error de tamano

#### Scenario: DOCX content type is allowed at fetch

- **WHEN** una respuesta final declara content-type DOCX OOXML
  (`application/vnd.openxmlformats-officedocument.wordprocessingml.document`)
- **AND** el tamano esta dentro del limite
- **THEN** el fetcher permite consumir el cuerpo (el parse lo resuelve el
  pipeline de ingestion)
