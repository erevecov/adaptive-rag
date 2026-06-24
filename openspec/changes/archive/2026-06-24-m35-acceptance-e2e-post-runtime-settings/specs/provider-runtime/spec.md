# provider-runtime Specification

## ADDED Requirements

### Requirement: Runtime settings acceptance proves effective provider resolution

El sistema MUST proveer un smoke publico que configure runtime settings
persistidos y ejecute el flujo local citado usando la resolucion efectiva de
providers.

#### Scenario: Acceptance configures model catalog and slots

- **WHEN** un usuario ejecuta el smoke de acceptance post-runtime-settings
- **THEN** el sistema crea o reutiliza una provider connection fake global
- **AND** sincroniza/persiste un catalogo de modelos para esa connection
- **AND** configura defaults globales para `chat`, `dense_embedding` y
  `contextualization`
- **AND** configura al menos un override por proyecto

#### Scenario: Acceptance uses persisted runtime resolution

- **WHEN** el smoke ejecuta indexing y chat para el proyecto creado
- **THEN** el provider de embeddings se resuelve desde el override efectivo del
  proyecto
- **AND** el chat runner se resuelve desde el default global heredado
- **AND** el resultado incluye citations

#### Scenario: Acceptance report does not expose secrets

- **WHEN** el smoke serializa su reporte JSON
- **THEN** incluye IDs de connections, modelos, catalogo y criterios
- **AND** no incluye API keys, Authorization headers, ciphertext ni valores de
  secrets

### Requirement: Hosted and local live acceptance remain opt-in

El smoke default MUST funcionar sin red ni credenciales hosted, y MUST tratar
Qwen/local live como acceptance manual opt-in.

#### Scenario: Default acceptance is local fake

- **WHEN** el smoke corre en una instalacion local default
- **THEN** no llama endpoints externos
- **AND** no requiere `ADAPTIVE_RAG_QWEN_API_KEY`
- **AND** reporta Qwen/local live como opt-in fuera del gate default
