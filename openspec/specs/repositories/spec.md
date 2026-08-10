# repositories Specification

## Purpose

Definir el contrato de repositories sincronicos que centralizan el acceso
persistente al dominio Adaptive RAG y mantienen aislamiento obligatorio por
`workspace_id`.
## Requirements
### Requirement: Repositories centralizan acceso persistente por workspace

El sistema MUST proveer repositories SQLAlchemy sincronicos que usen una `Session` inyectada y no creen transacciones propias.

#### Scenario: Crear workspace no hace commit implicito

- **WHEN** se crea un workspace desde el repository
- **THEN** la fila queda agregada y con `id` disponible despues de `flush`
- **AND** el caller sigue controlando `commit` o `rollback`

#### Scenario: Obtener workspace por id devuelve solo la fila pedida

- **WHEN** se consulta un workspace por `workspace_id`
- **THEN** el repository devuelve ese workspace si existe
- **AND** devuelve `None` si no existe

### Requirement: SourceRepository exige aislamiento por workspace_id

El sistema MUST filtrar todas las lecturas de sources por `workspace_id` explicito.

#### Scenario: Listado de sources no cruza workspaces

- **WHEN** existen sources con el mismo `external_id` en dos workspaces
- **THEN** listar sources para un `workspace_id` devuelve solo las filas de ese workspace

#### Scenario: Filtros tipados de source usan columnas conocidas

- **WHEN** se listan sources con `source_type`, `external_id` o `tag`
- **THEN** el resultado respeta esos filtros ademas de `workspace_id`

### Requirement: DocumentRepository mantiene pertenencia por workspace y source

El sistema MUST crear y consultar documents y document versions sin omitir el `workspace_id` del document.

#### Scenario: Documents se listan por workspace y opcionalmente por source

- **WHEN** un workspace tiene documents en multiples sources
- **THEN** listar documents por `workspace_id` devuelve solo ese workspace
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

#### Scenario: WorkspaceRepository lists workspaces without committing

- **WHEN** API or CLI lists workspaces
- **THEN** `WorkspaceRepository` returns workspaces in deterministic order
- **AND** the repository does not create, commit or rollback a transaction

#### Scenario: SourceRepository detects duplicate identity

- **WHEN** API or CLI creates a source
- **THEN** the authoring adapter can detect an existing source with the same
  `workspace_id`, `source_type` and `external_id`
- **AND** it can return a stable conflict before or after database constraint
  enforcement

### Requirement: Repositories support ingestion ops adapters

Repositories MUST expose enough workspace-scoped access for ingestion ops adapters
to avoid ad-hoc SQL in API and CLI layers.

#### Scenario: Job operations use caller-owned transactions

- **WHEN** ingestion ops list or requeue jobs through repositories
- **THEN** repository methods flush changes but do not commit or rollback
- **AND** API and CLI remain responsible for transaction boundaries
