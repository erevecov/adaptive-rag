# Diseno M6 de evals

## Contexto

M4 expuso retrieval como servicio/API/CLI con query text, filtros y citations.
M5 expuso chat/tool calling sobre ese retrieval compartido y mantuvo tests sin
red mediante providers/runners fake. Lo que falta es una frontera de evaluacion
que mida esos comportamientos como producto y no solo como unit/integration
tests de casos felices.

M6 debe construir un harness offline y reproducible. Debe usar las mismas
fronteras de servicio que API/CLI consumen, pero con datasets locales pequenos
que permitan detectar regresiones de retrieval y chat sin introducir
dependencias hosted.

## Objetivos

- Definir un contrato de datasets de evals versionados en el repo.
- Ejecutar casos de retrieval contra `RetrievalService` con provider fake.
- Ejecutar casos de chat contra `ChatService` con runner fake y retrieval fake
  o fixture-backed.
- Calcular metricas simples y auditables: hit rate de expected chunks,
  citation coverage, groundedness por evidencia esperada, errores por caso y
  pass/fail por umbrales.
- Emitir reportes JSON estables para uso local y CI.
- Agregar un comando CLI no interactivo para ejecutar evals offline.

## No objetivos

- No usar LLM-as-judge hosted.
- No llamar a OpenAI, Qwen, Cohere, Voyage u otros providers live.
- No crear UI, dashboards ni visualizaciones.
- No persistir historiales de conversaciones.
- No implementar streaming.
- No hacer tuning automatico de prompts, chunking o ranking.
- No agregar migraciones Alembic.

## Decisiones

### 1. Evals como paquete propio

La opcion recomendada es crear un paquete `adaptive_rag.evals` con archivos
pequenos por responsabilidad:

- `models.py`: dataclasses o modelos internos de cases, expected evidence y
  resultados.
- `datasets.py`: carga/validacion de fixtures versionados.
- `retrieval_runner.py`: evals de retrieval sobre `RetrievalService`.
- `chat_runner.py`: evals de chat sobre `ChatService`.
- `metrics.py`: calculo puro de metricas y umbrales.
- `reports.py`: serializacion JSON estable.

Esto mantiene evals separado de API/CLI/chat/retrieval y evita convertir un
solo archivo en un runner gigante.

Alternativa descartada: poner evals dentro de `tests/`. Sirve para cobertura,
pero no deja una herramienta reutilizable por CLI o CI como producto del repo.

### 2. Fixtures locales antes que datasets externos

Los datasets iniciales deben vivir en el repo bajo una carpeta dedicada como
`evals/fixtures/` o `tests/fixtures/evals/`, con documentos/casos pequenos y
expected citations explicitas. La implementacion puede cargar esos fixtures
para crear proyectos, sources, documents, chunks y embeddings fake.

Alternativa descartada: depender de un dataset remoto. Aumenta variabilidad,
red y mantenimiento antes de tener un harness estable.

### 3. Metricas simples, no juicio semantico hosted

M6 debe medir primero señales objetivas:

- retrieval: expected chunk en top-k, posicion, score disponible y filtros
  respetados.
- chat: citations esperadas presentes, citations desconocidas ausentes,
  snippets/evidence esperados mencionados o referenciados por el runner fake,
  tool calls esperadas.
- reportes: pass/fail por umbral y lista de errores por caso.

Alternativa descartada: evaluar answer quality con un juez LLM hosted. Es
valioso mas adelante, pero antes se necesita una base offline que no dependa de
credenciales ni costo.

### 4. CLI primero, API despues si hace falta

La superficie recomendada para M6 es un comando `adaptive-rag evals run` que
emita JSON. API de evals queda fuera de alcance porque los consumidores
iniciales son desarrollo local y CI.

Alternativa descartada: endpoint HTTP para ejecutar evals. Introduce riesgo de
operacion y seguridad sin necesidad para el milestone.

## Secuencia de M6

### 1. `m6-evals-fixtures-contract`

Crear el contrato de datasets y modelos de resultados.

Alcance:

- Paquete `adaptive_rag.evals`.
- Modelos internos para retrieval cases, chat cases, expected evidence,
  thresholds y resultados por caso.
- Loader de fixtures versionados con validacion estricta.
- Tests unitarios de parsing, errores y serializacion.

Fuera de alcance:

- CLI.
- Ejecucion sobre DB.
- Providers live.

### 2. `m6-retrieval-eval-runner`

Ejecutar casos de retrieval contra el servicio compartido.

Alcance:

- Runner que construye un proyecto fixture-backed en una session de test/local.
- Provider fake determinista para query embeddings.
- Metricas top-k y expected chunk hit.
- Reporte por caso con citations observadas.

Fuera de alcance:

- Chat.
- Rerank.
- Sparse/hybrid retrieval.

### 3. `m6-chat-eval-runner`

Ejecutar casos de chat contra el servicio compartido.

Alcance:

- Runner fake determinista que usa tool calling o respuestas controladas.
- Verificacion de expected citations, tool calls y ausencia de evidence
  inventada.
- Reutilizacion de `ChatService`, `RetrievalService` y payloads existentes.

Fuera de alcance:

- Modelos hosted.
- Streaming.
- Persistencia de conversaciones.

### 4. `m6-evals-cli-reporting`

Publicar la superficie operativa minima.

Alcance:

- `adaptive-rag evals run`.
- Flags para seleccionar suite, output path, thresholds y formato JSON.
- Exit code 0 cuando todos los thresholds pasan y 1 cuando hay regresiones.
- Reporte JSON estable con resumen y detalle por caso.

Fuera de alcance:

- UI.
- Dashboard.
- API HTTP.

### 5. `m6-quality-gate`

Cerrar M6 cuando los slices anteriores esten mergeados, validando tests, lint,
types, specs, smokes CLI y archivando el change.

## Riesgos y mitigaciones

- Riesgo: evals duplican logica de API/CLI.
  Mitigacion: runners deben depender de `RetrievalService`, `ChatService` y
  payloads compartidos.
- Riesgo: fixtures crecen sin estructura.
  Mitigacion: contrato estricto de dataset y loaders pequenos.
- Riesgo: metricas ambiguas o subjetivas.
  Mitigacion: empezar con metricas objetivas y reportes por caso.
- Riesgo: tests/evals requieren red.
  Mitigacion: providers y runners fake obligatorios.
- Riesgo: archivos gigantes.
  Mitigacion: paquete `adaptive_rag.evals` separado por modelos, loaders,
  runners, metricas y reportes.

## Validacion esperada por slice

Cada slice debe ejecutar:

```text
uv run pytest
uv run ruff check .
uv run mypy src
openspec validate m6-evals-plan --strict
openspec validate --specs --strict
```

Los slices de runner/CLI deben incluir un smoke de `adaptive-rag evals run`
contra fixtures locales.

