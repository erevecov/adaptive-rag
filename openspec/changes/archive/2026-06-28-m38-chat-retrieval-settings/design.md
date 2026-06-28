# Design M38 chat retrieval settings

## Decision

`rerank` queda encendido por defecto para chat, pero controlado por settings
persistidos. Los defaults globales definen el comportamiento inicial para
proyectos nuevos y para proyectos sin override. Cada proyecto puede overridear
`retrieval_limit`, `rerank_enabled` y `rerank_candidate_limit`.

Valores iniciales:

- `retrieval_limit=5`
- `rerank_enabled=true`
- `rerank_candidate_limit=10`
- maximo configurable para `retrieval_limit` y `rerank_candidate_limit`: `50`

## Architecture

Agregar un contrato pequeno de settings de retrieval de chat:

- `GlobalChatRetrievalSettings`: una fila global con defaults operativos.
- `ProjectChatRetrievalSettings`: override por proyecto.
- `ChatRetrievalSettingsRepository`: upsert/get global, upsert/delete project,
  y resolucion efectiva con source `global` o `project`.

El setting efectivo se inyecta en `ChatService`. `ChatRequest.retrieval_limit`
queda opcional para compatibilidad, pero cuando no se declara se usa el setting
efectivo. Si la request declara un limite explicito, se valida contra el maximo
y se usa solo para esa vuelta. `rerank_enabled` y `rerank_candidate_limit` salen
de settings efectivos; no se exponen como knobs publicos por mensaje en este
slice.

## Data flow

1. Admin global configura defaults en `/runtime-settings/chat/retrieval`.
2. Admin de proyecto puede configurar override en
   `/projects/{project_id}/runtime-settings/chat/retrieval`.
3. Chat API/CLI resuelven settings efectivos para el proyecto antes de crear
   `ChatService`.
4. `ChatRetrievalTool` ejecuta `RetrievalService.search()` con:
   - `strategy=dense_sparse`;
   - `limit=retrieval_limit`;
   - `rerank=RetrievalRerankOptions(candidate_limit=rerank_candidate_limit)`
     cuando `rerank_enabled=true`.
5. `RetrievalService` recupera hasta `candidate_limit`, reordena con el slot
   `rerank` efectivo y devuelve los top `retrieval_limit`.
6. Audit persiste strategy, `used_rerank`, scores, filtros, limite final,
   candidate limit y provider usage/cost.

## Validation

Validaciones:

- `retrieval_limit` debe estar entre `1` y `50`.
- `rerank_candidate_limit` debe estar entre `1` y `50`.
- Si `rerank_enabled=true`, `rerank_candidate_limit >= retrieval_limit`.
- Si `rerank_enabled=false`, `rerank_candidate_limit` igual se mantiene valido
  para permitir reactivar rerank sin reconfigurar.
- Chat no construye provider de rerank cuando `rerank_enabled=false`.
- Chat construye provider de rerank solo cuando el setting efectivo requiere
  rerank y una tool call de retrieval se ejecuta.

## Testing and measurement

La implementacion debe seguir TDD:

- Unit tests de modelos/repositorios para herencia global/proyecto.
- API tests de global/project chat retrieval settings.
- Chat service tests para default rerank, disabled rerank y limites invalidos.
- API/CLI chat tests para confirmar que los settings efectivos llegan al
  retrieval request.
- Eval o smoke offline que compare chat `dense_sparse` sin rerank contra chat
  con settings efectivos de rerank, serializando citation coverage y
  regresiones por caso cuando haya suite con casos de chat.

Hosted rerank sigue fuera del gate obligatorio; el path fake/local debe cubrir
CI y smoke default.
