# Diseno M9 de calidad de retrieval/rerank

## Contexto

M3 publico dense retrieval exacto sobre embeddings persistidos, con filtros
antes del ranking y citations ancladas. M4 agrego `RetrievalService`, API y CLI
sobre ese baseline. M6/M8 agregaron evals offline/hosted para medir calidad, y
M7 agrego el runtime de providers live con usage/cost y `rerank` como operacion
modelada, aunque todavia no existe provider de rerank.

M9 debe mejorar calidad de retrieval de forma incremental: dense sigue siendo
el default y rerank se agrega como etapa opt-in despues de recuperar un top-N de
candidatos ya filtrados. Cada cambio debe ser medible contra el baseline dense
y debe preservar citations, filtros, errores estables y reportes sin secretos.

## Objetivos

- Mantener retrieval dense como default en service, API, CLI y evals.
- Definir un contrato provider-neutral de rerank con fake default.
- Implementar Qwen rerank como provider live opt-in con usage/cost, budget
  guard, timeout y errores estables.
- Agregar una etapa rerank opcional en `RetrievalService` que reciba solo
  candidatos dense ya filtrados.
- Exponer knobs acotados de rerank en API/CLI sin romper payloads existentes.
- Comparar dense baseline vs reranked retrieval en evals hosted, incluyendo
  calidad, usage y costo.
- Cerrar M9 con specs canonicas y smokes live opt-in cuando `.env` local este
  disponible.

## No objetivos

- No convertir rerank en default.
- No agregar lexical retrieval, RRF ni sparse retrieval en M9.
- No agregar dashboards, UI ni endpoints HTTP de evals.
- No agregar LLM-as-judge, prompt tuning automatico ni auto-tuning de ranking.
- No agregar streaming, persistencia de conversaciones ni multi-turn memory.
- No persistir `retrieval_runs`, latencias o historiales de costo en base de
  datos.
- No cambiar el schema de chunks ni agregar migraciones Alembic.

## Decisiones

### 1. Rerank antes de lexical/RRF

La opcion recomendada es implementar rerank primero porque usa el pipeline
actual de candidatos dense y el runtime de providers ya preparado para usage,
costo y budgets. Lexical/RRF tiene mas blast radius: requiere indices,
normalizacion de texto para search, fusion de rankings y comparaciones nuevas.

Lexical/RRF queda como candidato para M10 si las evals de M9 muestran que dense
+ rerank no alcanza recall o cobertura en preguntas reales.

### 2. Dense default, rerank opt-in

`RetrievalService.search` debe conservar el comportamiento dense por defecto.
Rerank solo se activa con configuracion o parametros explicitos que declaren el
modo, candidate limit y top-k final.

Alternativa descartada: activar rerank automaticamente cuando exista una API
key. Eso haria que resultados, costos y latencia cambien por environment, lo
que romperia el baseline reproducible.

### 3. Rerank despues de filtros

El provider de rerank solo recibe candidatos que ya pasaron aislamiento por
`project_id` y `metadata_filter`. Rerank no puede ampliar el conjunto de
candidatos ni saltarse reglas de acceso; solo reordena o descarta dentro del
top-N dense.

### 4. Metadata de ranking explicita

Los resultados reranked deben conservar `distance`, `score` y `citation` del
baseline, y agregar metadata opcional de rerank como provider, modelo,
candidate rank, rerank score y motivo de fallback. Esa metadata debe ser
estable para API, CLI y evals, pero no debe incluir prompts completos,
documentos crudos adicionales ni secretos.

### 5. Evals comparativas antes de default

M9 no debe declarar rerank como estrategia recomendada por defecto sin una
comparacion hosted de calidad/costo contra dense baseline. La primera metrica
es retrieval hit/rank/citation coverage sobre las suites existentes; latencia y
costo se reportan como contexto operacional, no como gate absoluto.

## Secuencia de M9

### 1. `m9-rerank-provider-contract`

Crear el contrato provider-neutral y fake default.

Alcance:

- Protocolos/modelos para rerank requests, candidates, scores y metadata.
- Settings/factory para seleccionar provider fake o Qwen sin llamadas live.
- Errores estables de configuracion, candidates invalidos y budget.
- Tests unitarios sin red.

Fuera de alcance:

- Adaptador Qwen live.
- Integracion con `RetrievalService`.
- API/CLI final.

### 2. `m9-live-qwen-rerank-provider`

Implementar Qwen rerank bajo el contrato M9.

Alcance:

- Cliente Qwen rerank opt-in con credenciales via environment.
- Timeouts/retries acotados y sanitizacion de errores.
- Registro de usage/cost bajo operacion `rerank`.
- Smoke CLI opt-in para validar conectividad cuando `.env` local exista.
- Tests con cliente fake/monkeypatch, sin red.

Fuera de alcance:

- Ejecutar rerank dentro de retrieval productivo.
- Evals comparativas.

### 3. `m9-retrieval-rerank-service`

Integrar rerank opcional en `RetrievalService`.

Alcance:

- Candidate generation dense con `candidate_limit` acotado.
- Rerank solo despues de filtros dense.
- Fallback explicito cuando rerank esta deshabilitado o falla de forma
  recuperable.
- Resultados con metadata de rerank y citations preservadas.
- Tests unitarios y de servicio con fake reranker.

Fuera de alcance:

- Activar rerank en API/CLI por defecto.
- Persistir retrieval runs.

### 4. `m9-rerank-api-cli-surface`

Publicar la superficie operativa controlada.

Alcance:

- Parametros API/CLI para habilitar rerank y definir candidate limit/top-k
  dentro de limites seguros.
- Serializacion estable de metadata de rerank.
- Defaults dense compatibles con payloads actuales.
- Tests API/CLI sin credenciales live.

Fuera de alcance:

- UI/dashboard.
- CI con red.

### 5. `m9-rerank-hosted-evals`

Comparar dense baseline vs reranked retrieval.

Alcance:

- Runner o modo de eval que ejecute dense y reranked sobre la misma suite.
- Reporte JSON con metricas comparativas, usage y costo de rerank.
- Hosted opt-in con `--max-cost-usd`.
- Suite smoke pequena para validar Qwen rerank manualmente.

Fuera de alcance:

- LLM-as-judge.
- Tuning automatico de parametros.

### 6. `m9-quality-gate`

Cerrar M9 cuando los slices anteriores esten mergeados.

Alcance:

- Validar tests, lint, types, specs y evals offline.
- Validar que dense sigue siendo default.
- Ejecutar smokes hosted Qwen de rerank si `.env` local esta disponible.
- Archivar `m9-retrieval-quality-rerank-plan`.
- Publicar `openspec/specs/retrieval-quality/spec.md` como spec canonica.

## Riesgos y mitigaciones

- Riesgo: rerank cambia resultados por defecto.
  Mitigacion: parametros opt-in, tests de default dense y docs explicitas.
- Riesgo: rerank recibe documentos fuera del filtro.
  Mitigacion: candidate set viene solo de `DenseRetriever` con filtros ya
  aplicados.
- Riesgo: costo o latencia crecen por candidate sets grandes.
  Mitigacion: candidate limit acotado, presupuesto obligatorio en hosted evals
  y metadata de usage/cost.
- Riesgo: provider errors contaminan API/CLI con detalles sensibles.
  Mitigacion: errores estables y sanitizados, reportes sin keys, headers ni
  payloads crudos.
- Riesgo: evals comparan modelos incompatibles.
  Mitigacion: M9 reutiliza materializacion hosted de M8 y reporta provider/model
  por operacion.

## Validacion esperada por slice

Cada slice debe ejecutar:

```text
uv run pytest
uv run ruff check .
uv run mypy src
npx --yes @fission-ai/openspec validate m9-retrieval-quality-rerank-plan --strict
npx --yes @fission-ai/openspec validate --specs --strict
```

Los slices de CLI deben incluir smokes offline obligatorios. Los smokes hosted
con Qwen quedan opt-in y solo se ejecutan cuando hay `.env` local con
credenciales.
