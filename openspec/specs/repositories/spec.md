# repositories Specification

## Purpose

Definir el contrato de repositories sincronicos que centralizan el acceso
persistente al dominio Adaptive RAG y mantienen aislamiento obligatorio por
`project_id`.
## Requirements
### Requirement: Repositories centralizan acceso persistente por proyecto

El sistema MUST proveer repositories SQLAlchemy sincronicos que usen una `Session` inyectada y no creen transacciones propias.

#### Scenario: Crear proyecto no hace commit implicito

- **WHEN** se crea un proyecto desde el repository
- **THEN** la fila queda agregada y con `id` disponible despues de `flush`
- **AND** el caller sigue controlando `commit` o `rollback`

#### Scenario: Obtener proyecto por id devuelve solo la fila pedida

- **WHEN** se consulta un proyecto por `project_id`
- **THEN** el repository devuelve ese proyecto si existe
- **AND** devuelve `None` si no existe

### Requirement: SourceRepository exige aislamiento por project_id

El sistema MUST filtrar todas las lecturas de sources por `project_id` explicito.

#### Scenario: Listado de sources no cruza proyectos

- **WHEN** existen sources con el mismo `external_id` en dos proyectos
- **THEN** listar sources para un `project_id` devuelve solo las filas de ese proyecto

#### Scenario: Filtros tipados de source usan columnas conocidas

- **WHEN** se listan sources con `source_type`, `external_id` o `tag`
- **THEN** el resultado respeta esos filtros ademas de `project_id`

### Requirement: DocumentRepository mantiene pertenencia por proyecto y source

El sistema MUST crear y consultar documents y document versions sin omitir el `project_id` del document.

#### Scenario: Documents se listan por proyecto y opcionalmente por source

- **WHEN** un proyecto tiene documents en multiples sources
- **THEN** listar documents por `project_id` devuelve solo ese proyecto
- **AND** aplicar `source_id` restringe el resultado a ese source

#### Scenario: Versiones de document se devuelven ordenadas

- **WHEN** un document tiene multiples document versions
- **THEN** el repository las devuelve ordenadas por `version_number` ascendente

### Requirement: ChunkRepository preserva orden local de chunks

El sistema MUST consultar chunks por `document_version_id` en orden de `ordinal`.

#### Scenario: Chunks se recuperan en orden estable

- **WHEN** una document version tiene chunks con ordinales no insertados en orden
- **THEN** el repository devuelve los chunks ordenados por `ordinal`

### Requirement: Repositories support public authoring adapters

Repositories MUST expose the deterministic reads and writes required by public
API and CLI authoring surfaces while keeping transaction control with the caller.

#### Scenario: ProjectRepository lists projects without committing

- **WHEN** API or CLI lists projects
- **THEN** `ProjectRepository` returns projects in deterministic order
- **AND** the repository does not create, commit or rollback a transaction

#### Scenario: SourceRepository detects duplicate identity

- **WHEN** API or CLI creates a source
- **THEN** the authoring adapter can detect an existing source with the same
  `project_id`, `source_type` and `external_id`
- **AND** it can return a stable conflict before or after database constraint
  enforcement

### Requirement: Repositories support ingestion ops adapters

Repositories MUST expose enough project-scoped access for ingestion ops adapters
to avoid ad-hoc SQL in API and CLI layers.

#### Scenario: Job operations use caller-owned transactions

- **WHEN** ingestion ops list or requeue jobs through repositories
- **THEN** repository methods flush changes but do not commit or rollback
- **AND** API and CLI remain responsible for transaction boundaries
