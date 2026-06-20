# retrieval-quality Specification

## Purpose

Define la frontera canonica de mejoras de calidad de retrieval que mantienen
dense retrieval como default, agregan rerank opt-in sobre candidatos ya
filtrados y permiten comparar calidad, usage y costo sin convertir providers
hosted en requisito de CI.

## Requirements
### Requirement: Retrieval quality improvements son opt-in y medibles

El sistema MUST mantener dense retrieval como default y MUST requerir
habilitacion explicita para cualquier etapa de rerank.

#### Scenario: Dense retrieval sigue siendo el default

- **WHEN** una solicitud de retrieval no habilita rerank
- **THEN** `RetrievalService` ejecuta el flujo dense existente
- **AND** API, CLI y evals conservan payloads y ordenamiento dense compatibles
  con el baseline actual

#### Scenario: Rerank requiere configuracion explicita

- **WHEN** una solicitud habilita rerank
- **THEN** debe declarar un modo/provider soportado
- **AND** debe usar limites acotados para candidates y resultados finales
- **AND** el resultado reporta que rerank fue usado o explica el fallback

### Requirement: Rerank preserva filtros y citations

El sistema MUST aplicar rerank solo sobre candidatos que ya pasaron aislamiento
de proyecto y filtros de metadata, y MUST preservar citations del baseline.

#### Scenario: Rerank recibe solo candidatos prefiltrados

- **WHEN** retrieval ejecuta con `metadata_filter` y rerank habilitado
- **THEN** dense retrieval aplica `project_id` y `metadata_filter` antes de
  construir candidatos para rerank
- **AND** el provider de rerank no recibe chunks fuera de ese conjunto

#### Scenario: Resultados reranked preservan citations

- **WHEN** rerank reordena candidatos dense
- **THEN** cada resultado conserva `chunk_id`, `citation`, `distance` y `score`
  del candidato original
- **AND** puede agregar metadata de rerank sin modificar el texto citado

### Requirement: Provider rerank es budgeted y secret-safe

El sistema MUST ejecutar providers live de rerank solo en modo opt-in y MUST
registrar usage/cost sin exponer secretos.

#### Scenario: Qwen rerank valida configuracion antes de red

- **WHEN** Qwen rerank esta seleccionado pero faltan credenciales o endpoint
  requerido
- **THEN** el runtime devuelve un error estable de configuracion
- **AND** no envia candidatos a red

#### Scenario: Usage y costo se registran como rerank

- **WHEN** un provider rerank live responde o es bloqueado por budget
- **THEN** el tracker registra provider, modelo, operacion `rerank`, call count,
  usage disponible, costo estimado y outcome
- **AND** no registra API keys, headers ni payloads crudos del provider

### Requirement: API y CLI exponen knobs acotados de rerank

El sistema MUST exponer parametros de rerank que mantengan defaults dense y
limites seguros para llamadas hosted.

#### Scenario: API/CLI conservan default dense

- **WHEN** un usuario llama `POST /projects/{project_id}/retrieval/search` o
  `adaptive-rag retrieval search` sin flags de rerank
- **THEN** el sistema responde con resultados dense como antes
- **AND** no lee credenciales de rerank ni llama providers live

#### Scenario: API/CLI validan limites de rerank

- **WHEN** un usuario habilita rerank con candidate limit invalido, menor que
  el top-k final o mayor al maximo permitido
- **THEN** API/CLI devuelven error de validacion estable
- **AND** no llaman al provider de rerank

### Requirement: Evals comparan baseline dense contra rerank

El sistema MUST permitir comparar calidad/costo de dense baseline y reranked
retrieval sobre suites versionadas, con metricas agregadas y por caso que
permitan decidir si un cambio mejora, empata o degrada el baseline.

#### Scenario: Reporte hosted compara rankings

- **WHEN** una suite de retrieval se ejecuta con rerank habilitado
- **THEN** el reporte incluye metricas de baseline dense y reranked retrieval
  sobre los mismos casos
- **AND** incluye usage/cost de rerank cuando el provider live se usa

#### Scenario: Rerank hosted no es requisito de CI

- **WHEN** se ejecutan tests, lint, mypy o evals offline obligatorios
- **THEN** no requieren credenciales live
- **AND** no ejecutan rerank hosted salvo habilitacion explicita

#### Scenario: Suites declaran intencion del caso

- **WHEN** una suite declara casos de retrieval para comparar estrategias
- **THEN** cada caso puede declarar metadata acotada de intencion y dificultad
- **AND** el loader rechaza campos desconocidos o ambiguos

#### Scenario: Dataset pack cubre riesgos representativos

- **WHEN** se usa el dataset offline para decidir cambios de retrieval
- **THEN** incluye casos de exact match, paraphrase, distractors, metadata
  filters y multi-evidence
- **AND** marca casos donde rerank deberia ayudar o mantenerse estable

#### Scenario: Comparacion reporta regresiones por caso

- **WHEN** dense y reranked retrieval se ejecutan sobre el mismo caso
- **THEN** el reporte indica si el caso mejoro, empato o degrado frente a dense
- **AND** expone best-rank delta y evidence perdida o ganada cuando aplique
- **AND** agrega conteos de mejoras, empates, regresiones y delta promedio de
  best-rank

#### Scenario: Decision gate precede algoritmos nuevos

- **WHEN** se propone lexical/RRF, sparse retrieval o tuning automatico
- **THEN** el change debe declarar evidencia de evals suficiente para justificar
  el incremento
- **AND** debe documentar regresiones criticas, costo/latencia y comportamiento
  con filtros y citations antes de tocar retrieval productivo
- **AND** debe citar los decision gates de retrieval vigentes y declarar si la
  decision es proceed, hold, no-go o needs-more-data
