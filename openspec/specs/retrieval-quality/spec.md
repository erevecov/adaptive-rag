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

#### Scenario: Decision matrix precede estrategia nueva

- **WHEN** se abre un milestone para elegir entre candidate tuning, lexical/RRF
  o sparse retrieval
- **THEN** el change declara una decision matrix con opcion recomendada, estado
  proceed/hold/no-go y razon de cada opcion
- **AND** no implementa nuevos algoritmos, indexes o providers en el PR de
  decision

#### Scenario: Candidate limit tuning puede preceder nuevos providers

- **WHEN** la evidencia disponible ya mide dense vs rerank pero no demuestra un
  fallo que requiera indexes o providers nuevos
- **THEN** el primer experimento debe preferir parametros acotados de
  `candidate_limit`, top-k o rerank antes de lexical/RRF o sparse retrieval
- **AND** debe mantener dense retrieval como default hasta un quality gate
  posterior

#### Scenario: Candidate limit matrix agrupa casos por metadata

- **WHEN** se prepara un experimento de candidate limit sobre una suite
  versionada
- **THEN** el sistema puede construir una matriz de limites acotados que
  declara el `candidate_limit`, `case_count` y `max_case_limit`
- **AND** agrupa los casos por `intent` y `difficulty` cuando esa metadata
  existe
- **AND** rechaza limites duplicados, no positivos o menores al mayor `limit`
  declarado por la suite

#### Scenario: Candidate limit A/B runner serializa quality y costo

- **WHEN** una suite de retrieval se ejecuta para varios `candidate_limit`
  acotados
- **THEN** el runner ejecuta el baseline dense una vez y compara cada limite
  reranked contra ese baseline
- **AND** serializa una fila estable por limite con status, metricas de
  retrieval, `comparison_metrics` y `comparison_cases`
- **AND** agrega conteos de improvement, regression y tie por `intent` y
  `difficulty`
- **AND** incluye usage/cost por fila y total de corrida cuando el modo hosted
  provee tracker de usage

#### Scenario: Lexical o RRF requieren fallo lexical medido

- **WHEN** un change propone lexical retrieval o RRF
- **THEN** debe citar casos versionados donde dense/rerank no recuperan terminos,
  codigos, nombres o identificadores necesarios
- **AND** debe declarar como preserva `metadata_filter`, ordering estable y
  citations originales

#### Scenario: Sparse retrieval requiere docs provider actuales

- **WHEN** un change propone Qwen sparse retrieval o embeddings sparse
- **THEN** debe citar documentacion provider actual verificada antes de definir
  payloads, storage, reindex o costos
- **AND** debe mantener sparse retrieval opt-in hasta demostrar mejoras sin
  regresiones criticas

### Requirement: Expansion de evidencia precede nuevas estrategias de retrieval

El sistema MUST ampliar evidencia versionada de retrieval antes de abrir
lexical/RRF, sparse retrieval, nuevos providers o cambios de defaults.

#### Scenario: M12 declara gaps medidos antes de algoritmos

- **WHEN** se abre un change posterior a M11 para mejorar retrieval
- **THEN** el change declara la evidencia M11 que motiva el trabajo
- **AND** identifica las familias de riesgo a ampliar, incluyendo distractors y
  lexical misses
- **AND** no cambia ranking productivo, providers, storage ni defaults en el PR
  de planificacion

#### Scenario: Casos lexicales y distractors quedan versionados

- **WHEN** una suite agrega casos para decidir lexical/RRF o sparse retrieval
- **THEN** cada caso declara intent, difficulty y coverage notes suficientes
  para entender el riesgo medido
- **AND** puede declarar una `risk_family` estricta para separar
  `semantic_distractor`, `identifier_exact`, `metadata_guard`,
  `multi_evidence` y `rerank_regression`
- **AND** los expected evidence ids y distractors relevantes quedan versionados
  en la fixture
- **AND** el loader rechaza metadata desconocida o ambigua

#### Scenario: Matrix agrupa casos por familia de riesgo

- **WHEN** se prepara una matrix de candidate limits sobre una suite versionada
- **THEN** el sistema agrupa casos por `risk_family` cuando esa metadata existe
- **AND** usa `uncategorized` para suites antiguas sin familia de riesgo
- **AND** la serializacion expone conteos y case ids por familia de riesgo

#### Scenario: Reportes de evidencia listan regresiones primero

- **WHEN** un runner compara dense, rerank, candidate tuning u otra estrategia
- **THEN** el reporte lista por caso expected evidence observado, perdido o
  ganado
- **AND** agrupa gaps por intent, difficulty y risk family cuando esa metadata
  existe
- **AND** presenta regresiones antes que mejoras agregadas

#### Scenario: Decision refresh cierra M12 antes de implementar estrategias

- **WHEN** la suite ampliada se ejecuta para decidir el siguiente incremento de
  retrieval
- **THEN** la decision matrix declara estado proceed, hold, no-go o
  needs-more-data para lexical/RRF, sparse retrieval y candidate tuning
- **AND** conserva dense retrieval como default salvo que otro change posterior
  apruebe una promocion con evidencia nueva

### Requirement: Post-v1 retrieval expansion remains opt-in until gated

The system MUST treat post-v1 contextual, lexical, sparse, graph and hybrid
retrieval capabilities as opt-in until a strategy gate proves promotion is
safe.

#### Scenario: Expansion track preserves dense default

- **WHEN** post-v1 retrieval capabilities are implemented
- **THEN** `dense` retrieval remains the default path
- **AND** each new retrieval capability requires explicit API, CLI or eval
  selection
- **AND** dense remains the fallback when an opt-in branch cannot run

#### Scenario: Frontend polish follows stable retrieval contracts

- **WHEN** frontend polish is planned after v1
- **THEN** contextual retrieval, lexical/RRF and sparse retrieval must first
  expose stable backend contracts or be explicitly excluded from the polish
  scope
- **AND** the frontend must not invent modes that lack API/CLI/eval contracts

### Requirement: Advanced retrieval sequence is staged by risk

The system MUST implement advanced retrieval in a risk-ordered sequence before
comparing promotion decisions.

#### Scenario: Contextual retrieval precedes new candidate branches

- **WHEN** the post-v1 retrieval expansion begins
- **THEN** generated Contextual Retrieval is the first implementation milestone
- **AND** it reuses existing chunk context fields and embedding input contracts
- **AND** it measures dense retrieval with and without generated context

#### Scenario: Lexical and RRF precede sparse retrieval

- **WHEN** contextual retrieval has a stable contract
- **THEN** local lexical retrieval and RRF are implemented before Qwen sparse
- **AND** lexical retrieval preserves project isolation, metadata filters,
  stable ordering and original citations
- **AND** RRF only fuses candidate lists that already satisfy those constraints

#### Scenario: Sparse retrieval verifies provider docs before coding

- **WHEN** Qwen sparse or `dense_sparse` retrieval is implemented
- **THEN** the change verifies current provider documentation before defining
  request payloads, response parsing, storage, scoring or cost assumptions
- **AND** sparse retrieval remains opt-in until the strategy gate reports a
  promotion decision

### Requirement: Retrieval strategy gate decides promotion

The system MUST compare advanced retrieval modes before changing defaults or
frontend assumptions.

#### Scenario: Strategy gate compares all ready modes

- **WHEN** contextual, lexical/RRF and sparse retrieval are ready enough to
  evaluate
- **THEN** the gate compares dense, contextual dense, lexical, sparse, hybrid
  RRF, graph opt-in and rerank where available
- **AND** it reports quality, regressions, latency, cost, fallback, filter
  behavior and citation coverage
- **AND** it assigns each strategy a decision of `promote`, `keep_opt_in`,
  `hold`, `no_go` or `needs_more_data`

### Requirement: Lexical and RRF preserve retrieval safety invariants

The system MUST keep project isolation, metadata filters, stable ordering and
original citations across lexical and hybrid RRF retrieval.

#### Scenario: Lexical filters before ranking

- **WHEN** lexical retrieval receives a metadata filter
- **THEN** it applies `project_id` and metadata filters before ranking
- **AND** excludes chunks outside the project or filter scope

#### Scenario: RRF deduplicates candidates

- **WHEN** a chunk appears in both dense and lexical candidate lists
- **THEN** hybrid RRF emits the chunk once
- **AND** records the dense rank, lexical rank and RRF score in result metadata

#### Scenario: Rerank remains explicit

- **WHEN** lexical or hybrid RRF is requested without rerank options
- **THEN** no rerank provider is required or called
- **AND** rerank can still be applied only when explicit rerank options are
  supplied

### Requirement: Sparse retrieval preserves retrieval invariants

Sparse retrieval and dense_sparse fusion MUST preserve project isolation,
metadata filters and original citations.

#### Scenario: Sparse retrieval applies filters before scoring

- **WHEN** sparse retrieval is requested with source/document/tag/date filters
- **THEN** candidates outside those filters are excluded before ranking
- **AND** results never cross project boundaries

#### Scenario: Sparse citations use original chunk text

- **WHEN** sparse retrieval returns a result for a contextualized chunk
- **THEN** the citation snippet is sourced from the original normalized document
  text
- **AND** contextual summaries do not become citation snippets

#### Scenario: Sparse rows are reproducible

- **WHEN** sparse backfill stores a row
- **THEN** it records provider, model, input hash and index fingerprint metadata
- **AND** rerunning with the same inputs reuses the row instead of duplicating it
