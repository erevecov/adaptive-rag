# Diseno M10 de datasets y decision gates de retrieval

## Contexto

M9 publico `retrieval-quality` como spec canonica: dense retrieval sigue siendo
default, rerank es opt-in, las evals hosted pueden comparar dense vs reranked y
los reportes incluyen usage/cost. El harness ya permite validar que Qwen
rerank funciona, pero los fixtures disponibles son `retrieval-smoke`,
`retrieval-rerank-smoke` y `chat-smoke`; son deliberadamente pequenos.

M10 debe convertir ese harness en una base de decision. Antes de implementar
lexical/RRF, sparse retrieval o tuning automatico, necesitamos suites con
preguntas variadas, metadatos de intencion, metricas que muestren regresiones y
un criterio documentado para decidir si un cambio merece pasar de experimento a
superficie productiva.

## Objetivos

- Ampliar el contrato de evals de retrieval con metadata por caso que explique
  intencion, dificultad y modo esperado de recuperacion.
- Reportar metricas por caso y agregadas que distingan hit rate, best rank,
  matched count, missed expected evidence y degradaciones frente a dense.
- Crear un dataset pack pequeno pero mas representativo que cubra exact match,
  paraphrase, distractors, metadata filters, multi-evidence y casos donde
  rerank deberia ayudar o no deberia cambiar el resultado.
- Mejorar reportes comparativos dense vs rerank para clasificar cada caso como
  improvement, tie o regression.
- Documentar decision gates para permitir o rechazar futuros slices de
  lexical/RRF, sparse retrieval o tuning de parametros.
- Cerrar M10 con specs canonicas, docs actualizadas y smokes opt-in cuando
  `.env` local este disponible.

## No objetivos

- No implementar lexical retrieval, RRF ni sparse retrieval en este milestone
  de planificacion.
- No convertir rerank en default.
- No agregar dashboards, UI ni endpoints HTTP de evals.
- No agregar LLM-as-judge ni auto-tuning.
- No persistir `retrieval_runs`, latencias o historiales de costo en base de
  datos.
- No cambiar schema de documentos/chunks ni agregar migraciones Alembic.

## Decisiones

### 1. Dataset primero, algoritmo despues

La opcion recomendada es mejorar coverage de evals antes de agregar lexical/RRF.
Sin suites mas representativas, un algoritmo nuevo puede parecer mejor por un
smoke pequeno y aun asi degradar filtros, citations o preguntas faciles.

Alternativa descartada: implementar lexical/RRF inmediatamente despues de M9.
Tiene mas blast radius operativo y aun no existe un decision gate que diga que
la mejora compensa complejidad, latencia y mantenimiento.

### 2. `retrieval-quality` absorbe M10

M10 no crea una capacidad separada. La calidad de retrieval ya tiene una spec
canonica; este milestone la modifica para exigir datasets, metricas y decision
gates que controlan cualquier mejora posterior.

### 3. Reportes comparativos deben mostrar regresiones

El reporte de M9 indica metricas agregadas dense/rerank. M10 debe agregar una
lectura por caso: si rerank subio el mejor rank, lo mantuvo, lo bajo o perdio
evidence que dense encontraba. Esto evita aprobar cambios por promedio mientras
se rompen casos importantes.

### 4. Hosted sigue siendo opt-in

Las suites nuevas deben correr offline con fakes por defecto. Hosted evals con
Qwen siguen siendo manuales, presupuestadas y secret-safe; CI no depende de red.

### 5. Decision gates escritos antes de experimentar

Antes de abrir un slice de lexical/RRF o sparse retrieval, el change debe
declarar que evidencia se necesita: mejora minima, ausencia de regresiones
criticas, costo/latencia aceptable y comportamiento con filtros/citations.

## Secuencia de M10

### 1. `m10-eval-case-metrics`

Ampliar el contrato de resultados de evals para hacer visibles decisiones por
caso.

Alcance:

- Metadata opcional por `RetrievalEvalCase`: intent, difficulty y notas de
  cobertura.
- Serializacion estable de metricas por caso ya existentes y nuevas metricas
  necesarias para comparacion.
- Tests unitarios y CLI con fixtures pequenos.

Fuera de alcance:

- Cambiar el ranking productivo.
- Llamadas hosted.

### 2. `m10-retrieval-dataset-pack`

Agregar suites de retrieval mas representativas.

Alcance:

- Fixture offline versionado con casos de exact match, paraphrase, distractors,
  metadata filters y multi-evidence.
- Fixture hosted smoke ampliado que siga siendo pequeno y barato.
- Validacion de loader para metadata nueva y rechazo de campos ambiguos.

Fuera de alcance:

- Importar datasets externos grandes.
- LLM-as-judge.

### 3. `m10-rerank-ab-reporting`

Mejorar reportes comparativos dense vs rerank.

Alcance:

- Comparacion por caso entre dense y reranked: improvement, tie o regression.
- Agregados de improvement/regression counts y best-rank delta promedio.
- Reporte JSON estable para CLI y PR bodies.
- Tests con fake reranker deterministico.

Fuera de alcance:

- Persistencia de reportes en DB.
- Dashboard.

### 4. `m10-decision-gate-docs`

Documentar criterios para futuros algoritmos.

Alcance:

- Docs que definan cuando abrir lexical/RRF, sparse retrieval o tuning de
  candidate limits.
- Umbrales recomendados iniciales para aceptar experimentos: mejora agregada,
  cero regresiones criticas y costo/latencia documentados.
- Actualizacion de roadmap/progress con el siguiente slice recomendado.

Fuera de alcance:

- Implementar el algoritmo elegido.

### 5. `m10-quality-gate`

Cerrar M10 cuando los slices anteriores esten mergeados.

Alcance:

- Validar tests, lint, types, specs y evals offline.
- Ejecutar hosted evals Qwen opt-in si `.env` local esta disponible.
- Archivar `m10-retrieval-eval-datasets-plan`.
- Sincronizar cambios en `openspec/specs/retrieval-quality/spec.md`.

## Riesgos y mitigaciones

- Riesgo: suites crecen demasiado y vuelven lenta la validacion.
  Mitigacion: dataset pack pequeno, deterministic fixtures y hosted opt-in.
- Riesgo: metadata de casos se vuelve subjetiva.
  Mitigacion: campos acotados y validacion estricta del loader.
- Riesgo: reportes agregados esconden regresiones.
  Mitigacion: comparacion por caso y conteos de regression.
- Riesgo: M10 deriva hacia implementar lexical/RRF sin gate.
  Mitigacion: mantener algoritmos nuevos fuera del milestone hasta que un PR de
  decision documente evidencia suficiente.

## Validacion esperada por slice

Cada slice debe ejecutar:

```text
uv run pytest
uv run ruff check .
uv run mypy src
npx --yes @fission-ai/openspec validate m10-retrieval-eval-datasets-plan --strict
npx --yes @fission-ai/openspec validate --specs --strict
```

Los smokes hosted con Qwen quedan opt-in y solo se ejecutan cuando hay `.env`
local con credenciales.

