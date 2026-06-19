# Delta for provider-runtime

## ADDED Requirements

### Requirement: Provider runtime es opt-in y configurable

El sistema MUST mantener providers/runners fake como default y MUST requerir
configuracion explicita para habilitar llamadas live.

#### Scenario: Default local no llama red

- **WHEN** API, CLI, tests o evals offline solicitan un provider sin configurar
  live mode
- **THEN** el runtime usa providers/runners fake deterministas
- **AND** no lee credenciales ni llama providers hosted

#### Scenario: Provider live requiere credenciales explicitas

- **WHEN** la configuracion selecciona un provider live para embeddings o chat
- **THEN** la factory valida que existan credenciales requeridas en environment
- **AND** si faltan credenciales devuelve un error estable antes de llamar red
- **AND** no persiste ni serializa secretos en metadata, logs o responses

#### Scenario: Provider o modelo desconocido se rechaza

- **WHEN** la configuracion referencia un provider/modelo no soportado
- **THEN** el runtime devuelve un error estable de configuracion
- **AND** no instancia clientes live

### Requirement: Embeddings live cumplen el contrato dense existente

El sistema MUST exponer adapters live de embeddings mediante
`DenseEmbeddingProvider` y MUST conservar la dimension canonica de 1024.

#### Scenario: Embedding live valido produce metadata reproducible

- **WHEN** el pipeline de embeddings usa un provider live configurado
- **THEN** el adapter llama al provider seleccionado con los
  `embedding_input_text`
- **AND** devuelve vectores de 1024 dimensiones
- **AND** la metadata persistida incluye provider, modelo, dimension e input
  hash

#### Scenario: Dimension live incompatible falla antes de persistir

- **WHEN** el provider live devuelve un vector con dimension distinta de 1024
- **THEN** el pipeline devuelve un error estable de dimension
- **AND** no persiste embeddings parciales

#### Scenario: Retrieval query usa el mismo provider configurado

- **WHEN** `RetrievalService.search()` corre en live mode
- **THEN** genera el query embedding mediante la factory configurada
- **AND** valida dimension antes de llamar a `DenseRetriever`

### Requirement: Chat live usa tool calling verificable

El sistema MUST exponer runners live mediante `ChatRunner` y MUST conservar la
validacion de citations contra resultados devueltos por retrieval.

#### Scenario: Runner live llama la tool de retrieval existente

- **WHEN** `ChatService.respond()` usa un runner live configurado
- **THEN** el runner recibe la tool de retrieval existente
- **AND** cualquier citation devuelta debe corresponder a un result recuperado
- **AND** el servicio rechaza citations desconocidas con un error estable

#### Scenario: Runner live no cambia los contratos API/CLI

- **WHEN** API o CLI usan chat en live mode
- **THEN** siguen devolviendo `answer`, `citations` y metadata minima de tool
  calls con el mismo shape publico
- **AND** no exponen detalles de SDK ni secretos

### Requirement: Runtime aplica usage y limites de costo

El sistema MUST capturar metadata estructurada de llamadas live y MUST aplicar
limites configurables de uso/costo antes de completar una respuesta.

#### Scenario: Llamada live registra metadata minima

- **WHEN** un adapter live completa o falla una llamada
- **THEN** registra provider, modelo, outcome, duracion y usage disponible
- **AND** si el provider expone request id o tokens/unidades, la metadata los
  incluye
- **AND** si el provider no expone un campo, la metadata indica ausencia sin
  inventar valores

#### Scenario: Presupuesto excedido bloquea respuesta

- **WHEN** el costo estimado de una request o corrida supera el limite
  configurado
- **THEN** el runtime devuelve un error estable de presupuesto
- **AND** no emite una respuesta de chat ni persiste embeddings parciales

#### Scenario: Timeouts y retries son acotados

- **WHEN** un provider live tarda demasiado o falla transitoriamente
- **THEN** el runtime aplica timeout y retries configurados
- **AND** al agotar retries devuelve un error estable con metadata sin secretos

### Requirement: Smokes live son opt-in y evals offline siguen sin red

El sistema MUST separar smokes live de los tests obligatorios y MUST preservar
evals offline sin providers hosted.

#### Scenario: Suite obligatorio no requiere credenciales

- **WHEN** se ejecuta `uv run pytest` o `adaptive-rag evals run` con fixtures
  offline
- **THEN** no se requieren credenciales live
- **AND** no se hacen llamadas de red a providers hosted

#### Scenario: Smoke live requiere habilitacion explicita

- **WHEN** un usuario ejecuta un smoke live
- **THEN** debe habilitar live mode y proveer credenciales por environment
- **AND** el smoke usa inputs pequenos y limites de costo bajos
- **AND** si faltan credenciales, el smoke se omite o falla con mensaje estable

