# Diseno M8 de hosted evals

## Contexto

M6 creo `adaptive_rag.evals` con suites locales versionadas, runners
deterministas de retrieval/chat y reportes JSON. M7 agrego Qwen como provider
live opt-in para embeddings y chat, junto con usage/cost metadata y budget
guards. La combinacion permite correr evals con providers hosted, pero todavia
falta una frontera explicita que separe esos runs de los evals offline
obligatorios.

M8 debe agregar hosted evals como modo operacional pequeno y seguro. Debe
reutilizar `EvalSuite`, `RetrievalService`, `ChatService`, factories de
providers y `ProviderUsageTracker`; no debe introducir una segunda arquitectura
de evals ni hacer que CI dependa de red.

## Objetivos

- Mantener `adaptive-rag evals run` offline por defecto y sin credenciales.
- Agregar un modo hosted opt-in para evals de retrieval y chat con Qwen.
- Materializar evidence de fixtures con el mismo embedding provider live que se
  usara para queries de retrieval.
- Ejecutar chat hosted mediante `QwenChatRunner` sin saltarse la validacion de
  citations de `ChatService`.
- Capturar usage/cost por llamada y agregados por corrida en el reporte JSON.
- Aplicar presupuesto maximo de corrida y devolver errores estables cuando se
  excede.
- Proveer una suite hosted pequena para smoke manual y tests sin red mediante
  fakes/monkeypatches.

## No objetivos

- No reemplazar `evals-baseline`; los evals offline siguen siendo el gate de CI.
- No agregar LLM-as-judge hosted.
- No agregar dashboards, UI ni endpoints HTTP de evals.
- No agregar streaming, persistencia de conversaciones ni multi-turn memory.
- No agregar rerank hosted ni retrieval hibrido.
- No hacer tuning automatico de prompts, chunking, ranking o providers.
- No persistir historiales de costo en base de datos ni agregar migraciones.

## Decisiones

### 1. Hosted evals como modo explicito

La opcion recomendada es mantener un solo comando `adaptive-rag evals run`, pero
agregar un modo explicito como `--mode hosted` y exigir `--max-cost-usd`. Sin
ese modo, el comando conserva el comportamiento offline existente.

Alternativa descartada: crear un comando separado `evals hosted-run`. Separar
comandos reduce riesgo, pero duplicaria parsing, output y seleccion de suite.
Un modo explicito mantiene una superficie unica y testeable.

### 2. Reusar fixtures, re-embeddear con provider live

Hosted retrieval debe usar los mismos `EvalSuite` versionados, pero si el run
usa Qwen, la materializacion debe generar embeddings de evidence con Qwen y
usar Qwen tambien para query embeddings. Mezclar evidence fake con query live
haria que la metrica mida incompatibilidad artificial, no calidad real.

Alternativa descartada: exigir embeddings live precomputados en el fixture.
Eso haria dificil revisar diffs, aumentaria tamano del repo y acoplaria suites
pequenas a un modelo especifico.

### 3. Quality y costo en el mismo reporte

El reporte hosted debe extender el JSON existente con campos agregados de
provider usage:

- provider/model por operacion.
- call count por operacion.
- input/output/total tokens cuando existan.
- costo estimado por operacion y total de corrida.
- records bloqueados por presupuesto.
- indicacion de usage unavailable cuando el provider no reporte datos.

El reporte no debe incluir API keys, headers, prompts completos ni payloads
crudos del provider.

Alternativa descartada: depender solo de logs `provider_call`. Los logs sirven
para observabilidad, pero el resultado de evals necesita ser comparable en PRs y
archivos JSON.

### 4. Chat hosted conserva groundedness verificable

Los casos de chat hosted deben pasar por `ChatService`, que ya valida citations
contra resultados recuperados. M8 no debe introducir un judge LLM para calificar
respuestas; las metricas iniciales son citation coverage, tool call coverage,
errores de citations desconocidas y usage/cost.

Alternativa descartada: pedir al mismo modelo hosted que juzgue sus respuestas.
Eso introduce costo adicional, sesgo y otra superficie de prompts antes de tener
reportes hosted basicos.

## Secuencia de M8

### 1. `m8-hosted-eval-contract`

Crear el contrato de ejecucion hosted y reportes de usage/cost.

Alcance:

- Modelos internos para modo de eval `offline`/`hosted`.
- Agregados serializables de provider usage/cost por corrida y por operacion.
- Validacion de `--max-cost-usd` requerido para hosted mode.
- Errores estables para credenciales faltantes, provider no soportado y budget
  excedido.
- Tests unitarios sin red.

Fuera de alcance:

- CLI final.
- Llamadas live reales.
- Persistencia historica de costo.

### 2. `m8-live-retrieval-eval-runner`

Ejecutar casos de retrieval con embeddings live.

Alcance:

- Runner hosted de retrieval que materializa evidence con el provider live
  configurado.
- Query embeddings con el mismo provider/modelo.
- Reutilizacion de `RetrievalService` y fixtures existentes.
- Captura de usage/cost de embeddings en el reporte.
- Tests con provider fake que emula usage/cost, sin red.

Fuera de alcance:

- Rerank hosted.
- Sparse/hybrid retrieval.
- Datasets remotos.

### 3. `m8-live-chat-eval-runner`

Ejecutar casos de chat con runner live.

Alcance:

- Runner hosted de chat que usa `QwenChatRunner` via factory configurada.
- Reutilizacion de `ChatService`, `RetrievalService` y evidence materializada.
- Metricas de citation coverage, tool calls esperadas y errores por caso.
- Captura de usage/cost de chat y embeddings de retrieval.
- Tests con cliente fake/monkeypatch, sin red.

Fuera de alcance:

- LLM-as-judge.
- Streaming.
- Historial persistente.

### 4. `m8-evals-cli-hosted-mode`

Publicar la superficie operativa.

Alcance:

- `adaptive-rag evals run <suite> --mode hosted --max-cost-usd <value>`.
- Uso de settings/factories existentes para Qwen.
- Salida JSON extendida con `provider_usage`.
- Exit code estable para regresion de metricas, configuracion faltante y
  presupuesto excedido.
- Smoke live opt-in documentado con suite pequena.

Fuera de alcance:

- Ejecutar hosted evals en CI por defecto.
- UI/dashboard.
- API HTTP.

### 5. `m8-quality-gate`

Cerrar M8 cuando los slices anteriores esten mergeados.

Alcance:

- Validar tests, lint, types, specs y evals offline.
- Validar que hosted evals siguen opt-in.
- Ejecutar un smoke live de Qwen si `.env` local esta disponible.
- Archivar `m8-live-provider-evals-plan`.
- Publicar `openspec/specs/hosted-evals/spec.md` como spec canonica.

## Riesgos y mitigaciones

- Riesgo: hosted evals entran al gate obligatorio.
  Mitigacion: `--mode hosted` explicito, tests sin red y CI offline por
  defecto.
- Riesgo: costos no acotados durante una suite.
  Mitigacion: `--max-cost-usd` obligatorio y budget guard agregado por corrida.
- Riesgo: metricas de retrieval falsas por embeddings incompatibles.
  Mitigacion: evidence y queries usan el mismo embedding provider/modelo.
- Riesgo: secrets en reportes.
  Mitigacion: reportes solo incluyen provider/model/usage/cost y nunca headers
  ni keys.
- Riesgo: archivos de evals crecen demasiado.
  Mitigacion: modelos/reportes/runners hospedados separados por
  responsabilidad dentro de `adaptive_rag.evals`.

## Validacion esperada por slice

Cada slice debe ejecutar:

```text
uv run pytest
uv run ruff check .
uv run mypy src
npx --yes @fission-ai/openspec validate m8-live-provider-evals-plan --strict
npx --yes @fission-ai/openspec validate --specs --strict
```

Los slices de CLI deben incluir `adaptive-rag evals run` offline como smoke
obligatorio. Los smokes hosted con Qwen quedan opt-in y solo se ejecutan cuando
hay `.env` local con credenciales.

