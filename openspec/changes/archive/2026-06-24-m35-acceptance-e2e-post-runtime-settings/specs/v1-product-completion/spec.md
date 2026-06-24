# v1-product-completion Specification

## ADDED Requirements

### Requirement: Product completion includes post-runtime-settings acceptance

El producto MUST validar que runtime settings persistidos funcionan con el flujo
local completo despues de agregar provider connections, catalogo de modelos y
overrides por proyecto.

#### Scenario: Runtime acceptance complements v1 quality gate

- **WHEN** se evalua el producto despues de M34
- **THEN** el gate de acceptance ejecuta authoring, ingestion, indexing y chat
  citado con providers resueltos desde runtime settings persistidos
- **AND** conserva `adaptive-rag v1 quality-gate` como evidencia de release
  local-first
- **AND** no convierte Qwen hosted, providers locales ni graph en defaults

#### Scenario: Acceptance output is machine-readable

- **WHEN** el smoke termina correctamente
- **THEN** emite JSON con estado, criterios, evidencia de runtime settings,
  evidencia de first-run y sistemas opt-in diferidos
- **AND** cada criterio queda marcado como `passed`
