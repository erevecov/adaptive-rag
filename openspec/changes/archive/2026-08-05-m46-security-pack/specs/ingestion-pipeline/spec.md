## ADDED Requirements

### Requirement: Ingestion content guard redacts secrets before persistence

The system MUST run the content guard on `normalized_text` after parsing and
before computing content hash / creating a document version, so secret-like
literals are not indexed as-is.

#### Scenario: Ingest redacts secret-like markdown content

- **WHEN** an `ingest_source` job parses a text source whose body contains a
  secret-like token matching the content guard
- **THEN** the stored `document_versions.normalized_text` does not contain the
  original secret literal
- **AND** the job can still succeed when remaining text is non-empty
- **AND** extraction or parser metadata records that redactions occurred
