# Diseno M11 de decision de estrategia de retrieval

## Contexto

M9 entrego rerank opt-in y M10 agrego el dataset pack, metricas por caso,
`comparison_cases` y decision gates. El sistema ya puede medir si rerank ayuda,
empata o degrada frente a dense, pero no debe saltar directamente a
lexical/RRF o sparse retrieval sin una decision explicita.

M11 debe elegir el primer experimento medible despues de M10. La decision se
centra en tres opciones:

- tuning de `candidate_limit`, top-k y limites relacionados de rerank;
- lexical retrieval/RRF;
- Qwen sparse retrieval.

## Decision

La decision recomendada es `proceed` con tuning de `candidate_limit` como primer
experimento M11.

Lexical/RRF queda en `hold`: necesita fallos lexicales medidos que dense/rerank
no resuelvan y una estrategia de fusion que preserve filtros/citations.

Qwen sparse retrieval queda en `hold`: requiere verificar documentacion actual
de DashScope/Qwen antes de disenar adapter, storage, reindex y costos. En esta
PR se ejecuto `ctx7` para resolver Model Studio/DashScope; el fetch de Model
Studio no devolvio detalles utiles de embeddings, y DashScope solo quedo
resuelto como libreria candidata. Por eso el change no fija API syntax ni
payloads sparse.

## Objetivos

- Capturar una decision matrix de opciones de retrieval antes de escribir codigo.
- Definir una secuencia M11 enfocada en tuning de candidates sobre el harness
  dense/rerank existente.
- Mantener dense retrieval como default y cualquier tuning como opt-in hasta un
  quality gate posterior.
- Exigir que lexical/RRF y sparse retrieval citen evidencia de evals antes de
  abrir cambios de implementacion.
- Exigir verificacion de docs provider actuales antes de cualquier adapter Qwen
  sparse.

## No objetivos

- No implementar lexical search, RRF, sparse embeddings ni indexes nuevos.
- No cambiar defaults de retrieval/rerank.
- No agregar migraciones Alembic ni columnas para sparse vectors.
- No agregar nuevas llamadas live a providers.
- No modificar API/CLI de retrieval en este PR.
- No agregar dashboards, LLM-as-judge ni auto-tuning.

## Decision matrix

| Opcion | Estado | Razon |
| --- | --- | --- |
| `candidate_limit` tuning | `proceed` | Reutiliza dense/rerank, no requiere schema nuevo y puede medirse con `comparison_metrics` y `comparison_cases`. |
| lexical/RRF | `hold` | Todavia falta demostrar fallos lexicales concretos y disenar fusion con filtros/citations. |
| Qwen sparse retrieval | `hold` | Requiere docs actuales, storage/reindex y costo de embeddings antes de implementar. |

## Secuencia recomendada de M11

### 1. `m11-retrieval-strategy-decision`

Alcance:

- Crear el change OpenSpec M11.
- Documentar decision matrix y opcion recomendada.
- Actualizar progress/roadmap.

Fuera de alcance:

- Cambios runtime o provider.

### 2. `m11-candidate-limit-eval-matrix`

Alcance:

- Definir fixtures o parametrizacion de evals para comparar valores acotados de
  `candidate_limit`.
- Reutilizar `retrieval-dataset-pack` y reportar por intent/difficulty.
- Mantener offline como gate obligatorio y hosted Qwen como opt-in.

Fuera de alcance:

- Cambiar defaults productivos.

### 3. `m11-candidate-limit-ab-runner`

Alcance:

- Ejecutar dense/rerank contra varios candidate limits y serializar una tabla
  estable de quality/cost/regressions.
- Reportar cambios de `rerank_case_improvement_count`,
  `rerank_case_regression_count`, `rerank_best_rank_delta_avg` y usage cuando
  sea hosted.

Fuera de alcance:

- Persistir reportes en DB.

### 4. `m11-candidate-limit-api-cli-surface`

Alcance:

- Si el A/B runner justifica ajustes, exponer parametros o presets acotados sin
  cambiar el default dense.
- Validar limites antes de construir providers live.

Fuera de alcance:

- Promover candidate tuning a default global.

### 5. `m11-quality-gate`

Alcance:

- Validar tests, lint, types, specs y evals relevantes.
- Ejecutar smokes hosted Qwen opt-in si `.env` local esta disponible.
- Archivar `m11-retrieval-strategy-decision` cuando M11 quede cerrado.

## Riesgos y mitigaciones

- Riesgo: tuning de candidates mejore un caso y degrade otros.
  Mitigacion: comparar por caso y declarar regresiones primero.
- Riesgo: aumentar candidates suba costo/latencia sin mejora clara.
  Mitigacion: exigir cost/usage y limites explicitos.
- Riesgo: lexical/RRF o sparse entren por presion de roadmap.
  Mitigacion: dejarlos en hold hasta que un PR cite evidencia y docs actuales.
- Riesgo: docs de Qwen sparse cambien o no esten disponibles por `ctx7`.
  Mitigacion: no fijar API syntax aqui; exigir verificacion documental en el
  PR que proponga el adapter.

## Validacion esperada por slice

Cada slice debe ejecutar:

```text
uv run pytest
uv run ruff check .
uv run mypy src
npx --yes @fission-ai/openspec validate m11-retrieval-strategy-decision --strict
npx --yes @fission-ai/openspec validate --specs --strict
```

Los smokes hosted con Qwen quedan opt-in y solo se ejecutan cuando hay `.env`
local con credenciales.

