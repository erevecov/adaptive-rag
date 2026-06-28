# provider-runtime Specification

## Purpose
Define el runtime opt-in para providers live de embeddings y chat,
manteniendo fakes deterministas por defecto, credenciales explicitas,
limites de uso/costo, metadata sin secretos y smokes live separados de la
suite offline obligatoria.
## Requirements
### Requirement: Provider runtime es opt-in y configurable

El sistema MUST mantener providers/runners fake como default y MUST requerir
configuracion explicita para habilitar llamadas live.

#### Scenario: Default local no llama red

- **WHEN** API, CLI, tests o evals offline solicitan un provider sin configurar
  live mode
- **THEN** el runtime usa providers/runners fake deterministas
- **AND** no lee credenciales ni llama providers hosted

#### Scenario: Provider live requiere credenciales explicitas

- **WHEN** la configuracion efectiva selecciona un provider live para
  embeddings, chat o rerank
- **THEN** la factory valida que existan las credenciales requeridas en secrets
  persistidos globales o en fallback de environment
- **AND** si faltan credenciales devuelve un error estable antes de llamar red
- **AND** no persiste ni serializa secrets en metadata, logs o responses

#### Scenario: Provider o modelo desconocido se rechaza

- **WHEN** la configuracion referencia un provider/modelo no soportado por el
  slot efectivo
- **THEN** el runtime devuelve un error estable de configuracion
- **AND** no instancia clientes live

#### Scenario: Qwen live requiere API key y base URL

- **WHEN** la configuracion efectiva selecciona `qwen` como provider live para
  embeddings, chat, sparse embeddings o rerank
- **THEN** la factory exige una API key desde secret persistido global o desde
  `ADAPTIVE_RAG_QWEN_API_KEY`
- **AND** exige base URL desde la connection persistida o desde
  `ADAPTIVE_RAG_QWEN_BASE_URL`
- **AND** si falta cualquiera de esos valores devuelve un error estable antes
  de instanciar clientes live

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

#### Scenario: Smoke de embeddings live es un comando separado

- **WHEN** un usuario ejecuta `adaptive-rag providers embedding-smoke` con
  Qwen configurado
- **THEN** el comando llama al provider de embeddings configurado con un input
  pequeno
- **AND** emite JSON con provider, modelo, dimension y conteos
- **AND** no requiere base de datos ni ejecuta retrieval

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

### Requirement: Provider runtime supports sparse embeddings opt-in

The system MUST expose sparse embedding providers without changing the default
fake provider runtime or dense embedding contract.

#### Scenario: Qwen sparse embeddings use DashScope sparse output

- **WHEN** a live sparse provider is configured for Qwen
- **THEN** it requests DashScope text embeddings with `output_type=sparse`
- **AND** uses `text_type=document` for stored chunks
- **AND** uses `text_type=query` for retrieval queries
- **AND** parses each sparse item as `index`, `value` and optional `token`

#### Scenario: Qwen embeddings respect DashScope batch limits

- **WHEN** a live Qwen dense or sparse embedding request contains more than 10
  texts
- **THEN** the provider splits the request into batches of at most 10 texts
- **AND** returns embeddings in the original input order
- **AND** records provider usage for each network call without logging secrets

#### Scenario: Sparse provider records usage as embedding

- **WHEN** a sparse embedding provider call completes, fails or is blocked
- **THEN** provider usage uses operation `embedding`
- **AND** does not introduce a new provider usage operation value
- **AND** does not log or persist API keys

#### Scenario: Fake sparse provider is deterministic

- **WHEN** tests or offline evals request sparse embeddings without live mode
- **THEN** the fake sparse provider returns deterministic sparse vectors
- **AND** no network call is made

### Requirement: Runtime provider connections son globales

El sistema MUST modelar provider connections como configuracion global del
workspace local, no como secrets por proyecto.

#### Scenario: Hosted y local coexisten

- **WHEN** un usuario configura una connection hosted y una connection local
- **THEN** ambas quedan disponibles para slots distintos al mismo tiempo
- **AND** configurar una no deshabilita ni sobrescribe la otra

#### Scenario: Connection local no requiere secret hosted

- **WHEN** una connection local declara `base_url` y no declara secret requerido
- **THEN** el runtime puede usarla para slots compatibles sin API key hosted
- **AND** no intenta leer secrets de Qwen u otro provider hosted

#### Scenario: Secrets persistidos no se devuelven

- **WHEN** el usuario guarda o consulta el status de una connection con secret
- **THEN** el backend cifra el secret antes de persistirlo
- **AND** las respuestas solo incluyen estado seguro como `configured`,
  `updated_at` y fingerprint no reversible o `last_four`
- **AND** no incluyen plaintext, ciphertext ni headers de autenticacion

#### Scenario: Encryption key faltante bloquea writes de secrets

- **WHEN** falta o es invalida `ADAPTIVE_RAG_PROVIDER_SECRETS_KEY`
- **THEN** el endpoint que intenta guardar o descifrar un secret devuelve un
  error estable
- **AND** no persiste valores parciales
- **AND** endpoints que solo leen status no secreto pueden seguir respondiendo

### Requirement: Runtime slots son fijos y resolubles

El sistema MUST exponer un conjunto fijo inicial de slots de runtime y MUST
resolver cada operacion desde project override, default global o fallback
legacy.

#### Scenario: Slots soportados son finitos

- **WHEN** un usuario configura un runtime slot
- **THEN** el slot debe ser uno de `chat`, `dense_embedding`,
  `sparse_embedding`, `rerank` o `contextualization`
- **AND** cualquier otro valor se rechaza con `unsupported_slot`

#### Scenario: Project override gana sobre default global

- **WHEN** un proyecto define override para un slot
- **THEN** las operaciones de ese proyecto usan el override
- **AND** otros proyectos siguen usando el default global o su propio override

#### Scenario: Default global gana sobre environment

- **WHEN** un slot no tiene override de proyecto pero si tiene default global
  persistido
- **THEN** el runtime usa el default global
- **AND** no lee el provider/modelo legacy de `.env` para ese slot

#### Scenario: Environment sigue como fallback local

- **WHEN** no existe override de proyecto ni default global para un slot
- **THEN** el runtime puede usar la configuracion legacy de `.env` cuando existe
- **AND** si tampoco existe configuracion live valida, conserva fake fallback
  donde el contrato offline lo permite

#### Scenario: Slots pueden mezclar local y hosted

- **WHEN** un usuario configura `chat` con una connection local y `rerank` con
  Qwen hosted
- **THEN** una operacion puede usar ambos slots en la misma corrida
- **AND** el usage registra provider/modelo/slot de cada llamada sin conflicto

### Requirement: Chat slot soporta pool con un default

El sistema MUST permitir varios modelos habilitados para el slot `chat` y MUST
mantener exactamente un default efectivo por scope.

#### Scenario: Pool global de chat tiene default unico

- **WHEN** el usuario configura varios modelos para chat global
- **THEN** exactamente uno queda marcado como default
- **AND** las llamadas sin seleccion explicita usan ese default

#### Scenario: No se borra el ultimo modelo de chat

- **WHEN** el pool de chat tiene un solo modelo
- **THEN** el sistema rechaza borrar ese modelo con un error estable
- **AND** conserva el pool usable

#### Scenario: No se borra el default sin rotacion

- **WHEN** el usuario intenta borrar el modelo default de un pool con mas de un
  modelo
- **THEN** el sistema rechaza la operacion
- **AND** indica que primero debe rotar el default a otro modelo habilitado

#### Scenario: Proyecto puede overridear pool de chat

- **WHEN** un proyecto define su propio pool/default de chat
- **THEN** las llamadas de ese proyecto usan ese pool/default
- **AND** el pool global queda intacto para los proyectos que heredan defaults

### Requirement: Configuracion de proyecto no contiene secrets

El sistema MUST permitir overrides de runtime por proyecto sin guardar secrets
en tablas project-scoped.

#### Scenario: Override de proyecto referencia connection global

- **WHEN** un proyecto configura un slot para usar una hosted connection
- **THEN** el override guarda referencia a la connection y modelo
- **AND** el secret usado sigue siendo el secret global de la connection

#### Scenario: Reset vuelve a defaults globales

- **WHEN** el usuario elimina un override de proyecto
- **THEN** el proyecto vuelve a resolver ese slot desde defaults globales
- **AND** no elimina ni modifica connections, secrets o pools globales

#### Scenario: Responses de proyecto muestran herencia

- **WHEN** el frontend consulta runtime settings efectivos de un proyecto
- **THEN** la respuesta indica si cada slot es `inherited` u `overridden`
- **AND** no incluye secrets ni payloads raw de provider

### Requirement: Provider model catalog uses generated system IDs

El sistema MUST generar IDs internos de provider connection cuando el usuario
crea una connection desde las superficies de producto, y MUST persistir los IDs
reales de modelos separados de esos IDs internos.

#### Scenario: Connection create generates internal ID

- **WHEN** un usuario crea una provider connection sin indicar `connection_id`
- **THEN** el backend genera un ID interno estable y unico
- **AND** la respuesta devuelve ese ID para referencias futuras
- **AND** el usuario no necesita memorizar ni escribir ese ID

#### Scenario: Legacy upsert keeps explicit ID support

- **WHEN** un script o test usa `PUT /runtime-settings/connections/{id}`
- **THEN** el backend conserva ese contrato
- **AND** valida provider, tipo y capabilities igual que antes

### Requirement: Provider model catalog persists real model IDs

El sistema MUST mantener un catalogo global de modelos por provider connection
con IDs reales de provider y metadata segura.

#### Scenario: Model sync stores provider IDs

- **WHEN** un usuario sincroniza modelos para una provider connection
- **THEN** el backend consulta el provider o endpoint local configurado
- **AND** persiste cada `model_id` real bajo esa connection
- **AND** no persiste ni retorna API keys, Authorization headers ni ciphertext

#### Scenario: Model list can filter by slot capability

- **WHEN** el frontend solicita modelos para una connection y capability
- **THEN** el backend devuelve solo modelos catalogados compatibles
- **AND** incluye metadata segura y pricing solo si el provider lo entrego

#### Scenario: Pricing absence is explicit

- **WHEN** la API de listado del provider no devuelve pricing
- **THEN** el catalogo guarda `pricing` como `null`
- **AND** no inventa costos desde tablas externas ni defaults locales

#### Scenario: Provider listing failure is stable

- **WHEN** el provider no soporta model listing o responde con formato invalido
- **THEN** el sync devuelve un error estable
- **AND** conserva el catalogo previo sin exponer secretos

### Requirement: Runtime settings acceptance proves effective provider resolution

El sistema MUST proveer un smoke publico que configure runtime settings
persistidos y ejecute el flujo local citado usando la resolucion efectiva de
providers.

#### Scenario: Acceptance configures model catalog and slots

- **WHEN** un usuario ejecuta el smoke de acceptance post-runtime-settings
- **THEN** el sistema crea o reutiliza una provider connection fake global
- **AND** sincroniza/persiste un catalogo de modelos para esa connection
- **AND** configura defaults globales para `chat`, `dense_embedding` y
  `contextualization`
- **AND** configura al menos un override por proyecto

#### Scenario: Acceptance uses persisted runtime resolution

- **WHEN** el smoke ejecuta indexing y chat para el proyecto creado
- **THEN** el provider de embeddings se resuelve desde el override efectivo del
  proyecto
- **AND** el chat runner se resuelve desde el default global heredado
- **AND** el resultado incluye citations

#### Scenario: Acceptance report does not expose secrets

- **WHEN** el smoke serializa su reporte JSON
- **THEN** incluye IDs de connections, modelos, catalogo y criterios
- **AND** no incluye API keys, Authorization headers, ciphertext ni valores de
  secrets

### Requirement: Hosted and local live acceptance remain opt-in

El smoke default MUST funcionar sin red ni credenciales hosted, y MUST tratar
Qwen/local live como acceptance manual opt-in.

#### Scenario: Default acceptance is local fake

- **WHEN** el smoke corre en una instalacion local default
- **THEN** no llama endpoints externos
- **AND** no requiere `ADAPTIVE_RAG_QWEN_API_KEY`
- **AND** reporta Qwen/local live como opt-in fuera del gate default

### Requirement: Chat retrieval settings inherit globally and override per project

El sistema MUST permitir configurar settings operativos de retrieval de chat a
nivel global y pisarlos por proyecto sin mover secrets ni provider connections
al scope del proyecto.

#### Scenario: Global defaults define chat retrieval behavior

- **WHEN** no existe override de proyecto
- **THEN** el chat usa defaults globales efectivos para `retrieval_limit`,
  `rerank_enabled` y `rerank_candidate_limit`
- **AND** los defaults iniciales son `retrieval_limit=5`,
  `rerank_enabled=true` y `rerank_candidate_limit=10`

#### Scenario: Project override shadows global defaults

- **WHEN** un proyecto define override de chat retrieval settings
- **THEN** el chat usa los valores del proyecto
- **AND** la respuesta efectiva marca la fuente como `project`
- **AND** al borrar el override el proyecto vuelve a heredar defaults globales

#### Scenario: Limits are bounded

- **WHEN** un usuario configura `retrieval_limit` o `rerank_candidate_limit`
- **THEN** el sistema rechaza valores menores que `1` o mayores que `50`
- **AND** rechaza `rerank_candidate_limit < retrieval_limit` cuando
  `rerank_enabled=true`
