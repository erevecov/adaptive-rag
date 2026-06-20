# Diseno M12 de expansion de evidencia de retrieval

## Contexto

M10 agrego el dataset pack representativo y decision gates. M11 ejecuto tuning
de `candidate_limit` sobre ese harness y encontro una senal mixta: el agregado
puede mejorar con mas candidates, pero un caso distractor sigue degradando.
Esa es exactamente la clase de evidencia que debe bloquear defaults nuevos o
estrategias mas complejas hasta tener cobertura mas fuerte.

M12 debe medir mejor antes de construir. La decision central es ampliar la
evidencia sobre distractors y lexical misses, y solo despues decidir si
lexical/RRF, sparse retrieval o mas tuning pasan a `proceed`.

## Decision

La decision recomendada es `proceed` con expansion de evidencia de retrieval.

Lexical/RRF sigue en `hold`: puede ser el siguiente algoritmo, pero solo si M12
muestra fallos lexicales versionados donde dense/rerank no recuperan terminos,
codigos, nombres o identificadores.

Qwen sparse retrieval sigue en `hold`: requiere docs provider actuales,
storage/reindex, costo y una razon medible para preferir sparse sobre lexical o
rerank.

Candidate tuning sigue en `hold` para presets/defaults: M11 ya mostro mejora
agregada, pero tambien una regresion por caso.

## Objetivos

- Ampliar cobertura de evals antes de cambiar algoritmos o defaults.
- Capturar familias de riesgo de retrieval usando metadata estricta y
  versionada.
- Hacer visibles los gaps por caso: expected evidence perdido, distractor que
  desplaza evidencia, y tipo de fallo.
- Mantener dense retrieval como default durante todo M12.
- Producir una decision final `proceed`, `hold`, `no-go` o `needs-more-data`
  para lexical/RRF, sparse retrieval y candidate tuning.

## No objetivos

- No implementar lexical search, RRF, sparse embeddings ni indexes nuevos.
- No cambiar el contrato productivo de `RetrievalService`.
- No modificar defaults de dense retrieval ni rerank.
- No agregar providers live ni llamadas hosted obligatorias.
- No agregar migraciones Alembic ni columnas de storage.
- No crear dashboards, LLM-as-judge ni tuning automatico.

## Enfoque

### 1. Taxonomia de evidencia

M12 debe empezar con una taxonomia minima compatible con el loader actual:
`intent`, `difficulty` y `coverage_notes`. Si esos campos no alcanzan para
representar `lexical_miss`, `semantic_distractor`, `identifier_exact` o
`metadata_guard`, la ampliacion del schema debe ser explicita, testeada y
rechazar campos ambiguos.

### 2. Dataset pack ampliado

La suite debe incluir nuevos casos donde:

- el query depende de codigos, nombres, rutas, modelos o identificadores
  exactos;
- un distractor comparte semantica general pero no el contrato requerido;
- metadata filters excluyen evidencia tentadora;
- multi-evidence sigue necesitando todas las citas esperadas;
- rerank puede ayudar, empatar o degradar de forma deliberada.

### 3. Reporte de gaps

El reporte debe listar regresiones y gaps antes que mejoras agregadas. Como
minimo, debe exponer por caso:

- expected evidence observado/perdido;
- intent y difficulty;
- estrategia o parametro evaluado;
- decision del caso: improvement, tie, regression o unresolved;
- notas de cobertura relevantes.

### 4. Decision refresh

M12 termina con una decision matrix nueva. Esa decision no debe esconderse en
el agregado: lexical/RRF solo puede pasar a `proceed` si hay fallos lexicales
medidos y una estrategia de filtros/citations; sparse retrieval solo puede
pasar a `proceed` si hay docs actuales y un gap que lexical/rerank no cubre;
candidate tuning solo puede promoverse si no deja regresiones criticas.

## Secuencia recomendada de M12

### 1. `m12-retrieval-evidence-expansion`

Alcance:

- Crear el change OpenSpec M12.
- Documentar objetivos, no objetivos, riesgos y secuencia.
- Actualizar progress/roadmap y arquitectura.

Fuera de alcance:

- Cambios runtime, providers o fixtures.

### 2. `m12-evidence-case-taxonomy`

Alcance:

- Revisar si `case_metadata` actual alcanza para categorizar lexical misses y
  distractors.
- Si hace falta, ampliar el schema de metadata con campos estrictos y tests.
- Mantener compatibilidad con suites existentes.

Fuera de alcance:

- Implementar retrieval lexical.

### 3. `m12-distractor-lexical-dataset-pack`

Alcance:

- Agregar casos versionados de distractors, exact identifiers y lexical misses.
- Incluir expected evidence y coverage notes suficientes para auditar por caso.
- Mantener threshold offline claro y reproducible.

Fuera de alcance:

- Cambiar providers o ranking productivo.

### 4. `m12-evidence-gap-reporting`

Alcance:

- Agregar reporte o serializacion que agrupe gaps por intent/difficulty.
- Listar regresiones primero y preservar `comparison_cases`.
- Reutilizar runners existentes cuando sea suficiente.

Fuera de alcance:

- Persistir reportes en DB o crear dashboards.

### 5. `m12-strategy-decision-refresh`

Alcance:

- Ejecutar evals offline y, si `.env` local lo permite, smokes hosted Qwen
  opt-in.
- Publicar decision matrix actualizada para lexical/RRF, sparse retrieval y
  candidate tuning.
- Mantener defaults actuales si la evidencia queda mixta.

Fuera de alcance:

- Implementar la estrategia que resulte `proceed`; eso debe abrir otro change.

### 6. `m12-quality-gate`

Alcance:

- Validar tests, lint, types, specs y evals relevantes.
- Archivar `m12-retrieval-evidence-expansion` cuando M12 quede cerrado.

## Riesgos y mitigaciones

- Riesgo: M12 se convierta en lexical/RRF encubierto.
  Mitigacion: el change solo mide y decide; cualquier algoritmo posterior abre
  otro change.
- Riesgo: agregar campos de metadata demasiado flexibles.
  Mitigacion: mantener schema estricto y rechazar campos desconocidos.
- Riesgo: una mejora agregada o hosted tape una regresion offline.
  Mitigacion: ordenar reportes con regresiones primero.
- Riesgo: sparse retrieval avance sin docs actuales.
  Mitigacion: mantenerlo en `hold` hasta verificar provider, storage, reindex
  y costo en el PR que lo proponga.

## Validacion esperada por slice

Cada slice debe ejecutar:

```text
uv run pytest
uv run ruff check .
uv run mypy src
npx --yes @fission-ai/openspec validate m12-retrieval-evidence-expansion --strict
npx --yes @fission-ai/openspec validate --specs --strict
```

Los smokes hosted con Qwen quedan opt-in y solo se ejecutan cuando hay `.env`
local con credenciales y budget explicito.
