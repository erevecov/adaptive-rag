# Diseno M7 de provider runtime

## Contexto

M3 definio embeddings densos con `DenseEmbeddingProvider` y fake determinista.
M4 reutilizo ese provider para `RetrievalService`. M5 introdujo `ChatService`
con un `ChatRunner` inyectable y un runner local que responde con retrieval. M6
agrego evals offline sobre fakes. Esa arquitectura ya separa servicios,
adapters API/CLI y contratos internos; lo que falta es una capa de runtime que
conecte providers live sin romper determinismo ni introducir costos invisibles.

Hoy `adaptive_rag.retrieval.providers.get_default_dense_embedding_provider()`
retorna siempre `FakeDenseEmbeddingProvider`, y
`RetrievalGroundedChatRunner` es local sin red. M7 debe convertir esos puntos de
inyeccion en factories configurables y observables, manteniendo fake como modo
por defecto.

## Objetivos

- Definir settings de provider runtime con defaults locales seguros.
- Crear factories que seleccionen provider/modelo por configuracion y fallen
  temprano cuando faltan credenciales requeridas.
- Agregar un adapter live de embeddings compatible con la dimension canonica de
  1024 y la metadata de embeddings existente.
- Agregar un runner live de chat que pueda usar la tool de retrieval de
  `ChatService` sin duplicar retrieval.
- Registrar usage/cost metadata por llamada y aplicar limites configurables
  antes de responder.
- Mantener evals offline y tests unitarios sin red.
- Definir smokes live opt-in que se salten cuando faltan credenciales.

## No objetivos

- No cambiar el contrato publico de `POST /retrieval/search`,
  `adaptive-rag retrieval search`, `POST /chat` ni `adaptive-rag chat ask`.
- No agregar streaming.
- No persistir historiales de conversaciones.
- No agregar dashboards, UI ni endpoints de observabilidad.
- No agregar auth multiusuario.
- No implementar rerank hosted ni retrieval hibrido.
- No hacer tuning automatico de prompts, chunking, ranking o providers.
- No introducir llamadas live en evals offline.
- No agregar migraciones Alembic salvo que un slice posterior demuestre que la
  metadata en memoria/logs no alcanza para usage/cost.

## Decisiones

### 1. Fake por defecto, live opt-in

La opcion recomendada es mantener fake providers/runners como default y exigir
configuracion explicita para live mode. Esto preserva `uv run pytest`,
`adaptive-rag health`, evals offline y desarrollo local sin credenciales.

Alternativa descartada: activar live providers automaticamente cuando existe
una API key. Eso hace que tests/smokes dependan de estado externo y costos.

### 2. Factories pequenas en vez de providers globales

Las dependencias API/CLI deben pedir providers/runners a factories que leen
settings. Las factories deben devolver objetos que cumplen los Protocols
existentes (`DenseEmbeddingProvider`, `ChatRunner`) y deben producir errores
estables si el provider configurado no esta soportado o carece de credenciales.

Alternativa descartada: instanciar clientes live directamente dentro de
servicios como `RetrievalService` o `ChatService`. Eso mezclaria orquestacion de
producto con SDKs externos y dificultaria fakes.

### 3. Usage/cost como frontera transversal

Cada llamada live debe devolver o registrar metadata minima:

- provider y modelo.
- request id si el SDK lo expone.
- tokens o unidades de embedding cuando existan.
- costo estimado en USD si hay precio configurado.
- duracion, timeout/retry count y outcome.

El runtime debe aplicar limites configurables por request/corrida antes de
emitir respuesta cuando el costo estimado supera el presupuesto. Si el provider
no expone usage suficiente, el sistema debe reportar metadata parcial de forma
estable y no inventar valores.

Alternativa descartada: medir costo solo en logs libres. Logs ayudan, pero el
contrato necesita campos estructurados que tests y smokes puedan validar.

### 4. Live smokes son opt-in y pequenos

Los smokes live deben ejecutarse solo cuando el usuario los habilita
explicitamente y existen credenciales. Deben usar fixtures pequenos, limites
bajos y comandos separados del suite offline obligatorio.

Alternativa descartada: incluir smokes live en `uv run pytest` por defecto. Eso
rompe reproducibilidad, aumenta costo y falla en entornos sin credenciales.

## Secuencia de M7

### 1. `m7-provider-settings-contract`

Crear el contrato de configuracion del runtime.

Alcance:

- Settings para modo `fake`/`live`, provider/modelo de embeddings, provider/modelo
  de chat, timeouts, retries y limites de costo.
- Factories compartidas para API/CLI que mantienen fakes por defecto.
- Errores estables para provider desconocido, modelo incompatible o credenciales
  faltantes.
- Tests unitarios de settings/factories sin red.

Fuera de alcance:

- SDK live.
- Llamadas HTTP.
- Persistencia de usage/cost.

### 2. `m7-live-embedding-provider`

Agregar el adapter live de embeddings.

Alcance:

- Implementacion de `DenseEmbeddingProvider` live para el provider elegido por
  configuracion.
- Validacion de dimension 1024 antes de persistir o usar query embeddings.
- Timeouts/retries acotados y errores estables.
- Tests con cliente fake/monkeypatch, sin red.
- Smoke live opt-in documentado y separado.

Fuera de alcance:

- Sparse embeddings live.
- Rerank hosted.
- Cambio de dimension canonica.

### 3. `m7-live-chat-runner`

Agregar el runner live de chat/tool calling.

Alcance:

- Implementacion de `ChatRunner` live que pueda llamar la tool de retrieval
  existente.
- Prompt/contract minimo para devolver answer y cited chunk ids verificables.
- Rechazo de citations no devueltas por retrieval usando la validacion actual de
  `ChatService`.
- Tests con modelo/cliente fake, sin red.
- Smoke live opt-in documentado y separado.

Fuera de alcance:

- Streaming.
- Historial persistente.
- Multi-turn memory.
- Tool calling externo distinto a retrieval.

### 4. `m7-usage-cost-limits`

Agregar accounting y limites operativos.

Alcance:

- Modelos internos para usage/cost metadata.
- Budget guard por request/corrida configurable.
- Logging estructurado de provider calls sin secretos.
- Exposicion minima de metadata en logs/resultados internos donde aplique.
- Tests de limites, metadata parcial y errores de presupuesto.

Fuera de alcance:

- Dashboard.
- Facturacion real.
- Persistencia historica obligatoria.

### 5. `m7-quality-gate`

Cerrar M7 cuando los slices anteriores esten mergeados.

Alcance:

- Validar tests, lint, types, specs y smokes fake.
- Validar que smokes live son opt-in y quedan documentados.
- Archivar `m7-provider-runtime-plan`.
- Publicar `openspec/specs/provider-runtime/spec.md` como spec canonica.

## Riesgos y mitigaciones

- Riesgo: providers live entran en tests obligatorios.
  Mitigacion: fake default, smokes live opt-in y tests con clientes fake.
- Riesgo: secrets aparecen en logs o reportes.
  Mitigacion: settings no serializan API keys y logs usan redaction explicita.
- Riesgo: costos invisibles o no acotados.
  Mitigacion: budget guard y metadata estructurada por llamada live.
- Riesgo: SDKs externos contaminan servicios core.
  Mitigacion: adapters en runtime/factories que implementan Protocols existentes.
- Riesgo: chat live inventa citations.
  Mitigacion: `ChatService` conserva la resolucion de citations contra results
  recuperados.
- Riesgo: provider devuelve dimension incompatible.
  Mitigacion: validar dimension antes de persistir embeddings o ejecutar
  retrieval.

## Validacion esperada por slice

Cada slice debe ejecutar:

```text
uv run pytest
uv run ruff check .
uv run mypy src
openspec validate m7-provider-runtime-plan --strict
openspec validate --specs --strict
```

Los slices live deben incluir tests sin red con cliente fake/monkeypatch. Los
smokes live deben ser comandos separados y opt-in; no son requisito para el
suite obligatorio cuando faltan credenciales.

