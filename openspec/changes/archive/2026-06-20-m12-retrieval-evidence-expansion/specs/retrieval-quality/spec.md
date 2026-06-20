# retrieval-quality Specification

## ADDED Requirements

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
