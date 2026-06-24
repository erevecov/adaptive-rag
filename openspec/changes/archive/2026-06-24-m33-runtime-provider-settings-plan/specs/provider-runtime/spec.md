# provider-runtime Specification

## MODIFIED Requirements

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

## ADDED Requirements

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
