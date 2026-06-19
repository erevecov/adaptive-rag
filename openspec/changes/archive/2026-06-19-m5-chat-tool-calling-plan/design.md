# Diseno M5 de chat/tool calling

## Contexto

M4 cerro una superficie de retrieval con tres propiedades importantes para
chat: `RetrievalService` recibe query text y filtros, los query embeddings se
generan mediante provider inyectado/fake, y API/CLI comparten payloads
serializables con citations. M5 debe construir sobre esa frontera sin volver a
implementar retrieval en cada superficie.

La dependencia `pydantic-ai-slim[openai]` ya existe en el proyecto. Segun la
documentacion actual de Pydantic AI, `Agent` soporta dependency injection,
tools tipadas mediante `RunContext` y modelos de test como `TestModel` y
`FunctionModel`. M5 puede usar esa capacidad, pero debe encapsularla detras de
un contrato propio para mantener API/CLI y tests desacoplados del framework.

## Objetivos

- Definir un servicio conversacional compartido que acepte pregunta, proyecto,
  limite y filtros opcionales.
- Exponer retrieval como tool tipada que reutiliza `RetrievalService`.
- Devolver una salida estructurada con `answer`, citations y metadata minima
  de tool calls.
- Permitir tests deterministas sin red ni credenciales live.
- Mantener API y CLI como adaptadores delgados sobre el mismo servicio.

## No objetivos

- No persistir conversaciones ni memoria de sesiones.
- No implementar streaming.
- No agregar auth/API keys.
- No obligar providers live ni llamadas externas en tests.
- No cambiar ranking, rerank, sparse retrieval, RRF ni filtros de M4.
- No crear migraciones Alembic.

## Decisiones

### 1. Servicio propio antes que endpoint directo

La opcion recomendada es crear un `ChatService` en un modulo nuevo
`adaptive_rag.chat`, con dataclasses de request/response y errores estables.
API y CLI solo deben traducir entrada/salida.

Alternativa descartada: implementar chat directamente en FastAPI o Typer. Es
mas rapido, pero duplicaria el wiring de retrieval, filtros y serializacion.

### 2. Pydantic AI detras de un runner interno

El servicio debe depender de una abstraccion pequena de runner/modelo
conversacional. La implementacion inicial puede usar Pydantic AI para tool
calling, pero el resto del codigo debe conocer el contrato interno, no detalles
de `Agent`.

Alternativa descartada: exponer `Agent` en rutas, CLI o tests de alto nivel.
Eso acopla M5 al framework y complica cambios futuros.

### 3. Retrieval como tool tipada

La tool de retrieval debe aceptar query, limit y filtros tipados equivalentes a
M4, llamar a `RetrievalService.search()` y devolver payloads serializables. No
debe llamar a `DenseRetriever` ni construir embeddings por su cuenta.

Alternativa descartada: pasar snippets pre-recuperados al modelo sin tool
calling. Reduce riesgo, pero no valida el objetivo central de M5.

### 4. Respuesta estructurada con citations

El output de chat debe incluir texto de respuesta y citations derivadas de los
resultados de retrieval. La respuesta no debe inventar citation ids; solo puede
referenciar citations que la tool devolvio.

Alternativa descartada: respuesta de texto plano. Seria simple para CLI, pero
perderia el contrato verificable que despues necesita API, evals y UI.

## Secuencia de M5

### 1. `m5-chat-service-contract`

Crear el modulo de dominio conversacional y el contrato compartido.

Alcance:

- `adaptive_rag.chat` con request/response dataclasses o modelos internos.
- `ChatService` con dependencias inyectadas: runner conversacional y
  `RetrievalService`.
- Tool de retrieval tipada que reutiliza `RetrievalService`.
- Fakes deterministas para tests de servicio.
- Errores estables para prompt vacio, limite invalido, filtros invalidos y
  respuesta con citations desconocidas.

Fuera de alcance:

- Endpoint HTTP.
- CLI.
- Persistencia de conversaciones.
- Providers live obligatorios.

### 2. `m5-chat-api-endpoint`

Agregar el endpoint minimo de chat sobre el servicio compartido.

Alcance:

- `POST /projects/{project_id}/chat`.
- Request JSON con `message`, `retrieval_limit` y `metadata_filter`.
- Response JSON con `answer`, `citations` y metadata minima de tool calls.
- Dependency overrides para session, retrieval provider y runner fake.

Fuera de alcance:

- Streaming.
- Historial persistido.
- Auth.

### 3. `m5-chat-cli-command`

Agregar `adaptive-rag chat ask` sobre el mismo servicio.

Alcance:

- Flags de proyecto, pregunta, retrieval limit y filtros tipados.
- Salida JSON estable por defecto para tests automatizados.
- Manejo de errores consistente con API.

Fuera de alcance:

- Chat interactivo.
- Streaming terminal.
- Configuracion de providers live por CLI.

### 4. `m5-quality-gate`

Cerrar M5 cuando los slices anteriores esten mergeados, validando tests, lint,
types, specs y docs, y archivando el change.

## Riesgos y mitigaciones

- Riesgo: el framework de agentic runtime contamina API/CLI.
  Mitigacion: ocultarlo detras de un runner interno y tests del servicio.
- Riesgo: chat responde sin evidencia o con citations inventadas.
  Mitigacion: response estructurada y validacion contra citations devueltas por
  la tool.
- Riesgo: tests requieren red o credenciales.
  Mitigacion: fakes obligatorios y modelos de test deterministas.
- Riesgo: el servicio de chat se vuelve un archivo gigante.
  Mitigacion: separar contrato, service, tools, payloads y providers dentro de
  `adaptive_rag.chat`.
- Riesgo: filtros divergen de M4.
  Mitigacion: reutilizar `RetrievalMetadataFilter` o un mapper compartido, no
  crear un segundo contrato incompatible.

## Validacion esperada por slice

Cada slice debe ejecutar:

```text
uv run pytest
uv run ruff check .
uv run mypy src
openspec validate m5-chat-tool-calling-plan --strict
openspec validate --specs --strict
```

Los slices de API/CLI deben incluir tests de serialization y manejo de errores.
