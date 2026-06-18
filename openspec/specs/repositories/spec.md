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
