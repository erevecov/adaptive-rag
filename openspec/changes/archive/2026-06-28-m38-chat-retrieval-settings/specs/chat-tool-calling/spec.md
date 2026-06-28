# Delta for chat-tool-calling

## MODIFIED Requirements

### Requirement: Chat tool calling usa retrieval compartido

El sistema MUST exponer chat mediante un servicio compartido que puede llamar a
una tool de retrieval tipada y MUST reutilizar `RetrievalService` para obtener
contexto. El chat MUST resolver settings efectivos de retrieval por proyecto
antes de ejecutar la tool.

#### Scenario: Chat llama retrieval con settings efectivos

- **WHEN** una solicitud de chat incluye `project_id` y `message`
- **THEN** el servicio conversacional resuelve `retrieval_limit`,
  `rerank_enabled` y `rerank_candidate_limit` desde defaults globales y
  overrides de proyecto
- **AND** la tool llama a `RetrievalService.search()` con `strategy=dense_sparse`
  y filtros tipados
- **AND** si `rerank_enabled=true`, la llamada usa
  `RetrievalRerankOptions(candidate_limit=rerank_candidate_limit)`
- **AND** la tool devuelve resultados serializables con citations

#### Scenario: Request puede acotar retrieval limit de la vuelta

- **WHEN** una solicitud de chat declara `retrieval_limit`
- **THEN** el servicio usa ese limite solo para la vuelta actual
- **AND** valida que el limite este entre `1` y `50`
- **AND** si rerank esta activo, valida que el candidate limit efectivo sea
  mayor o igual al limite final

### Requirement: Chat permite tests deterministas sin red

El sistema MUST permitir ejecutar la capa conversacional con runners y
providers fake, sin llamadas a red ni credenciales live.

#### Scenario: Rerank default usa provider fake/local en tests

- **WHEN** los tests ejecutan una solicitud de chat con settings efectivos
  `rerank_enabled=true`
- **THEN** el servicio puede construir un reranker fake o inyectado
- **AND** reordena candidatos sin llamar providers hosted
- **AND** la respuesta y citations siguen siendo deterministicas

#### Scenario: Rerank disabled no construye provider rerank

- **WHEN** los settings efectivos tienen `rerank_enabled=false`
- **THEN** chat ejecuta retrieval sin `RetrievalRerankOptions`
- **AND** no construye ni valida credenciales de provider rerank
