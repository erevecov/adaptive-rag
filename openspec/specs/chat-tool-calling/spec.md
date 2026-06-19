# chat-tool-calling Specification

## Purpose
Define el contrato conversacional minimo sobre la superficie estable de
retrieval: un servicio compartido que expone retrieval como tool tipada y
adaptadores API/CLI delgados con respuestas citables.

## Requirements
### Requirement: Chat tool calling usa retrieval compartido

El sistema MUST exponer chat mediante un servicio compartido que puede llamar a
una tool de retrieval tipada y MUST reutilizar `RetrievalService` para obtener
contexto.

#### Scenario: Chat llama retrieval como tool

- **WHEN** una solicitud de chat incluye `project_id`, `message` y
  `retrieval_limit`
- **THEN** el servicio conversacional registra una tool de retrieval disponible
  para el runner/modelo
- **AND** la tool llama a `RetrievalService.search()` con query text y filtros
  tipados
- **AND** la tool devuelve resultados serializables con citations

#### Scenario: Chat no duplica dense retrieval

- **WHEN** el servicio conversacional necesita contexto documental
- **THEN** no instancia `DenseRetriever` directamente
- **AND** no genera query embeddings fuera de la superficie M4

### Requirement: Chat produce respuestas con citations verificables

El sistema MUST devolver una respuesta estructurada con texto de respuesta,
citations y metadata minima de tool calls, y MUST impedir references a
citations que no fueron devueltas por retrieval.

#### Scenario: Respuesta cita solo resultados recuperados

- **WHEN** la tool de retrieval devuelve citations para chunks recuperados
- **THEN** la respuesta de chat puede incluir esas citations
- **AND** cada citation visible corresponde a un payload devuelto por la tool

#### Scenario: Citation desconocida se rechaza

- **WHEN** el runner/modelo devuelve una respuesta que referencia una citation
  no presente en los resultados de retrieval
- **THEN** el servicio devuelve un error estable
- **AND** no emite una respuesta con evidencia inventada

### Requirement: Chat permite tests deterministas sin red

El sistema MUST permitir ejecutar la capa conversacional con runners y
providers fake, sin llamadas a red ni credenciales live.

#### Scenario: Runner fake ejecuta tool calling

- **WHEN** los tests ejecutan una solicitud de chat con runner fake
- **THEN** el runner fake puede solicitar la tool de retrieval
- **AND** el test verifica la respuesta y citations sin llamar a providers
  hosted

#### Scenario: Prompt invalido no llama al runner

- **WHEN** una solicitud de chat incluye `message` vacio o
  `retrieval_limit` invalido
- **THEN** el servicio devuelve un error estable
- **AND** no llama al runner ni a retrieval

### Requirement: Chat publica API y CLI minimas

El sistema MUST proveer un endpoint FastAPI y un comando Typer que usen el
mismo servicio conversacional.

#### Scenario: API retorna respuesta con citations

- **WHEN** `POST /projects/{project_id}/chat` recibe una solicitud valida
- **THEN** retorna `answer`, `citations` y metadata minima de tool calls
- **AND** usa el mismo servicio conversacional que la CLI

#### Scenario: CLI usa el mismo contrato que API

- **WHEN** `adaptive-rag chat ask` recibe proyecto, pregunta, limite y filtros
- **THEN** llama al mismo servicio conversacional que la API
- **AND** emite una salida JSON estable para tests automatizados
