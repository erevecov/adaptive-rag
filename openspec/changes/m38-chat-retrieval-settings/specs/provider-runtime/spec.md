# Delta for provider-runtime

## ADDED Requirements

### Requirement: Chat retrieval settings inherit globally and override per project

El sistema MUST permitir configurar settings operativos de retrieval de chat a
nivel global y pisarlos por proyecto sin mover secrets ni provider connections
al scope del proyecto.

#### Scenario: Global defaults define chat retrieval behavior

- **WHEN** no existe override de proyecto
- **THEN** el chat usa defaults globales efectivos para `retrieval_limit`,
  `rerank_enabled` y `rerank_candidate_limit`
- **AND** los defaults iniciales son `retrieval_limit=5`,
  `rerank_enabled=true` y `rerank_candidate_limit=10`

#### Scenario: Project override shadows global defaults

- **WHEN** un proyecto define override de chat retrieval settings
- **THEN** el chat usa los valores del proyecto
- **AND** la respuesta efectiva marca la fuente como `project`
- **AND** al borrar el override el proyecto vuelve a heredar defaults globales

#### Scenario: Limits are bounded

- **WHEN** un usuario configura `retrieval_limit` o `rerank_candidate_limit`
- **THEN** el sistema rechaza valores menores que `1` o mayores que `50`
- **AND** rechaza `rerank_candidate_limit < retrieval_limit` cuando
  `rerank_enabled=true`
