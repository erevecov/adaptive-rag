# retrieval-quality Specification

## MODIFIED Requirements

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

