# knowledge-lifecycle Specification

## Purpose

Definir el ciclo de vida de conocimiento: watermarks de content-hash por
fuente, resync por el camino publico de jobs, y reporte de dedup por hash
compartido sin borrado automatico.
## Requirements
### Requirement: Sources record content-hash sync watermarks after ingest

After a successful `ingest_source` job the system MUST record the resulting
content hash and sync timestamp on the source for lifecycle observability.

#### Scenario: Successful ingest marks source synced

- **WHEN** ingest completes for a source
- **THEN** source metadata includes `last_content_hash` and `last_synced_at`
- **AND** sync-status reports `synced`

### Requirement: Resync enqueues public ingest without privileged inline path

The system MUST allow contributor-level resync that enqueues `ingest_source`
for an existing source id.

#### Scenario: Resync creates ingest job

- **WHEN** a contributor requests resync for a source
- **THEN** a new `ingest_source` job is queued for that source

### Requirement: Dedup report groups shared content hashes

The system MUST provide a project-scoped report of document versions that share
the same content hash without automatically deleting data.

#### Scenario: Two sources with identical content appear in one group

- **WHEN** two sources ingest identical normalized text
- **THEN** the dedup report includes one group with count 2

