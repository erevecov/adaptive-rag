# hosted-evals Specification

## Purpose
Define evals hosted opt-in sobre las suites versionadas de M6 y el runtime de
providers de M7, manteniendo CI offline por defecto y reportando calidad,
usage y costo sin exponer secretos.

## Requirements
### Requirement: Hosted evals son opt-in y presupuestadas

El sistema MUST mantener evals offline como default y MUST requerir
habilitacion explicita para ejecutar evals contra providers hosted.

#### Scenario: Evals offline siguen sin red

- **WHEN** un usuario ejecuta `adaptive-rag evals run` sin habilitar hosted
  mode
- **THEN** la suite usa providers/runners fake o deterministas
- **AND** no lee credenciales ni llama providers hosted

#### Scenario: Hosted mode requiere presupuesto explicito

- **WHEN** un usuario ejecuta evals en hosted mode
- **THEN** debe declarar un presupuesto maximo de corrida
- **AND** el runtime bloquea la corrida o respuesta cuando el costo estimado
  supera el presupuesto
- **AND** el reporte identifica el bloqueo sin exponer secretos

#### Scenario: Credenciales faltantes fallan antes de llamar red

- **WHEN** hosted mode selecciona Qwen pero faltan credenciales requeridas
- **THEN** el comando devuelve un error estable de configuracion
- **AND** no ejecuta casos ni materializa fixtures live

### Requirement: Hosted retrieval evals reutilizan suites y services

El sistema MUST ejecutar retrieval hosted sobre `EvalSuite` versionados y MUST
reutilizar `RetrievalService` con el provider live configurado.

#### Scenario: Evidence y query usan el mismo embedding provider

- **WHEN** un caso de retrieval hosted se ejecuta
- **THEN** la materializacion genera embeddings de evidence con el provider live
  configurado
- **AND** la query usa el mismo provider y modelo para generar el query
  embedding
- **AND** la dimension se valida antes de ejecutar retrieval

#### Scenario: Resultado conserva metricas objetivas

- **WHEN** un caso de retrieval hosted termina
- **THEN** el reporte incluye expected evidence, observed evidence, best rank,
  hit y errores por caso
- **AND** el status de la suite respeta los thresholds declarados

### Requirement: Hosted chat evals conservan citations verificables

El sistema MUST ejecutar chat hosted mediante `ChatService` y MUST conservar la
validacion de citations contra resultados devueltos por retrieval.

#### Scenario: Runner live usa retrieval existente

- **WHEN** un caso de chat hosted se ejecuta
- **THEN** el runner live recibe la tool de retrieval existente
- **AND** cualquier citation devuelta debe corresponder a evidence recuperada
- **AND** citations desconocidas hacen fallar el caso con error estable

#### Scenario: Reporte de chat mide groundedness inicial

- **WHEN** un caso de chat hosted termina
- **THEN** el reporte incluye citation coverage, tool calls observadas,
  expected evidence y errores por caso
- **AND** no usa LLM-as-judge hosted para calificar la respuesta

### Requirement: Reportes hosted unen calidad, usage y costo

El sistema MUST extender los reportes JSON hosted con metadata agregada de
provider usage y costo sin incluir secretos.

#### Scenario: Reporte agrega provider usage

- **WHEN** una suite hosted termina o se bloquea por presupuesto
- **THEN** el reporte incluye provider, modelo, operacion, call count, usage
  disponible, costo estimado y outcome agregado
- **AND** si el provider no reporta usage, el reporte marca usage unavailable
  sin inventar tokens

#### Scenario: Reporte no expone secretos ni payloads crudos

- **WHEN** el reporte hosted se serializa
- **THEN** no incluye API keys, headers, authorization values, prompts completos
  ni responses crudas del provider
- **AND** solo expone campos estructurados necesarios para comparar calidad y
  costo

### Requirement: Hosted evals publican una CLI controlada

El sistema MUST proveer una superficie CLI no interactiva para correr hosted
evals y MUST mantener CI offline por defecto.

#### Scenario: CLI hosted requiere modo explicito

- **WHEN** un usuario ejecuta
  `adaptive-rag evals run <suite> --mode hosted --max-cost-usd <value>`
- **THEN** el comando usa settings/factories configuradas para providers live
- **AND** emite JSON a stdout o a un output path con resultados y provider
  usage

#### Scenario: Hosted evals no son requisito de CI

- **WHEN** se ejecuta la suite obligatoria de tests o evals offline
- **THEN** no requiere credenciales live
- **AND** no ejecuta hosted evals salvo que el usuario lo habilite
