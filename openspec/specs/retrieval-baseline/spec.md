# retrieval-baseline Specification

## Purpose

Definir el baseline de dense retrieval exacto sobre embeddings persistidos,
aplicando filtros antes del ranking y devolviendo citations ancladas al texto
normalizado original.
## Requirements
### Requirement: Retrieval baseline rankea embeddings densos exactos

El sistema MUST implementar retrieval dense exacto sobre `chunks.embedding`
persistidos y MUST validar que el query embedding use la dimension baseline de
1024.

#### Scenario: Query dense devuelve chunks ordenados por distancia

- **WHEN** un proyecto tiene chunks con embeddings densos persistidos
- **THEN** retrieval rankea candidatos por distancia L2 ascendente
- **AND** aplica `limit` despues del ranking

#### Scenario: Dimension incorrecta se rechaza

- **WHEN** el query embedding no tiene 1024 dimensiones
- **THEN** retrieval devuelve un error estable de dimension
- **AND** no ejecuta ranking

### Requirement: Retrieval baseline filtra antes de rankear

El sistema MUST aplicar `project_id` y filtros tipados antes de ordenar
candidatos por similitud.

#### Scenario: Project isolation bloquea candidatos cross-project

- **WHEN** otro proyecto tiene un chunk mas cercano al query embedding
- **THEN** retrieval para el proyecto solicitado no devuelve ese chunk

#### Scenario: Filtros de source y document restringen candidatos

- **WHEN** se pasan filtros por `source_id`, `document_id`, `source_type`,
  `tags` o rangos de fecha soportados
- **THEN** retrieval rankea solo los chunks que cumplen esos filtros

### Requirement: Retrieval baseline devuelve citations originales

El sistema MUST devolver un payload de citation basado en
`document_versions.normalized_text`, offsets de chunk y metadata de source.

#### Scenario: Citation usa texto original del chunk

- **WHEN** retrieval retorna un chunk con `contextual_summary`
- **THEN** el snippet visible viene de
  `document_versions.normalized_text[char_start:char_end]`
- **AND** no usa el contexto generado como evidencia factual visible
