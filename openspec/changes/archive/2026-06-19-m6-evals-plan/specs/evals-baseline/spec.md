# Delta for evals-baseline

## ADDED Requirements

### Requirement: Evals usan datasets locales versionados

El sistema MUST definir datasets de evaluacion offline versionados en el repo,
con casos pequenos para retrieval y chat anclados a evidence esperada.

#### Scenario: Dataset declara casos y expectations

- **WHEN** una suite de evals se carga desde fixtures locales
- **THEN** cada caso declara un identificador estable, tipo de eval, input y
  expected evidence o citations
- **AND** el loader valida campos requeridos antes de ejecutar servicios

#### Scenario: Dataset invalido falla antes de ejecutar servicios

- **WHEN** una suite omite campos requeridos o referencia expected evidence
  inexistente
- **THEN** la ejecucion falla con un error estable
- **AND** no llama a providers, retrieval ni chat

### Requirement: Evals ejecutan retrieval y chat sin red

El sistema MUST ejecutar evals con providers/runners fake o deterministas y
MUST reutilizar `RetrievalService` y `ChatService`.

#### Scenario: Retrieval eval usa el servicio compartido

- **WHEN** un caso de retrieval se ejecuta
- **THEN** el runner usa `RetrievalService.search()` con query text, limit y
  filtros declarados por el caso
- **AND** usa un provider fake o determinista para query embeddings
- **AND** no llama a providers hosted

#### Scenario: Chat eval usa el servicio compartido

- **WHEN** un caso de chat se ejecuta
- **THEN** el runner usa `ChatService.respond()` con runner fake o
  determinista
- **AND** verifica citations y tool calls contra expectations declaradas
- **AND** no llama a providers hosted

### Requirement: Evals producen metricas y reportes reproducibles

El sistema MUST emitir resultados por caso, metricas agregadas y pass/fail por
umbrales en un formato JSON estable.

#### Scenario: Reporte JSON incluye detalle y resumen

- **WHEN** una suite de evals termina
- **THEN** el reporte incluye resultados por caso, metricas agregadas,
  thresholds usados y estado final
- **AND** el orden de resultados es estable para diffs y CI

#### Scenario: Regresion produce exit code estable

- **WHEN** una suite no alcanza un threshold configurado
- **THEN** el comando de evals termina con exit code 1
- **AND** el reporte identifica los casos y metricas fallidas

### Requirement: Evals publican una CLI minima

El sistema MUST proveer un comando no interactivo para ejecutar suites offline
de evals y consumir sus reportes en CI.

#### Scenario: CLI ejecuta suite offline

- **WHEN** `adaptive-rag evals run` recibe una suite local valida
- **THEN** ejecuta los casos sin red
- **AND** emite JSON a stdout o a un output path configurado

#### Scenario: CLI rechaza suites desconocidas

- **WHEN** `adaptive-rag evals run` recibe una suite inexistente
- **THEN** devuelve un error estable
- **AND** termina con exit code 1

