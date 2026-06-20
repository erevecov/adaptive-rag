# Decision gates de retrieval

Fecha: 2026-06-20
Estado: linea base de decision para experimentos posteriores a M10

Este documento define cuando abrir o rechazar futuros cambios de retrieval como
lexical/RRF, sparse retrieval o tuning de `candidate_limit`. OpenSpec sigue
siendo la fuente de verdad para contratos implementados; este documento fija el
criterio de producto y calidad que debe citar el proximo change antes de tocar
ranking productivo.

## Principio

M10 mide antes de construir otro algoritmo. Un cambio de retrieval solo se abre
si explica que problema medido resuelve, que casos protege y que costo agrega.
La intuicion, un smoke aislado o una mejora promedio sin lectura por caso no son
evidencia suficiente.

## Evidencia minima

Todo change que proponga lexical/RRF, sparse retrieval o tuning de retrieval
debe declarar:

- Suite usada: al menos `evals/fixtures/retrieval-dataset-pack.json` o una
  suite nueva que cubra los mismos riesgos.
- Baseline: reporte dense actual y, si aplica, reporte dense vs rerank con
  `comparison_metrics` y `comparison_cases`.
- Regresiones: lista de casos `regression` con `lost_evidence_ids`, impacto y
  mitigacion propuesta.
- Filtros y citations: evidencia de que `metadata_filter` se aplica antes de
  rankear/fusionar y de que citations siguen apuntando al texto original.
- Costo y latencia: estimacion o medicion para nuevas llamadas/provider work,
  incluyendo `provider_usage` cuando haya providers hosted.
- Rollback: forma de mantener dense como default o de deshabilitar el cambio
  por configuracion.

## Umbrales iniciales

Estos umbrales son conservadores para abrir un experimento. Promoverlo a default
requiere otro change y evidencia nueva.

- `retrieval_hit_rate` no debe bajar frente a dense baseline en la suite
  representativa.
- `rerank_case_regression_count` o el conteo equivalente del experimento debe
  ser `0` para casos criticos: `exact_match`, `metadata_filter` y
  `multi_evidence`.
- `rerank_case_improvement_count` o conteo equivalente debe ser mayor que el
  conteo de regresiones para cambios que agregan complejidad.
- `rerank_best_rank_delta_avg` o delta equivalente debe ser mayor o igual a
  `0.0`; si es negativo, el change debe declararse no-go salvo que resuelva un
  blocker critico documentado.
- Cualquier incremento de costo o latencia debe venir con un limite explicito:
  top-k, candidate limit, timeout, budget o flag opt-in.
- Los smokes hosted con Qwen siguen siendo opt-in; CI obligatorio no puede
  depender de credenciales live.

## Gate para lexical/RRF

Abrir lexical/RRF es razonable solo si los reportes muestran uno de estos
problemas:

- dense/rerank falla casos de exactitud lexical donde la respuesta depende de
  terminos exactos, codigos, nombres o identificadores;
- casos con distractors comparten semantica pero se separan mejor por terminos
  lexicales;
- la mejora propuesta mantiene filtros y citations sin provider hosted nuevo.

No abrir lexical/RRF si el dataset actual no contiene el fallo, si la mejora se
ve solo en ejemplos manuales o si introduce regresiones en metadata filters.

## Gate para sparse retrieval

Abrir sparse retrieval es razonable solo si dense, lexical/RRF o rerank dejan
fallos medidos que sparse embeddings pueden resolver de forma plausible:

- queries con vocabulario parcialmente distinto al evidence;
- casos donde lexical exacto es demasiado rigido y dense no separa distractors;
- necesidad medible de recall adicional antes de rerank.

El change debe declarar storage, scoring, filtros, costo de embedding y plan de
reindex. Sparse no debe entrar como default; debe ser opt-in por proyecto o por
estrategia de eval hasta pasar un quality gate.

## Gate para tuning de candidate limits

Tuning de `candidate_limit`, top-k o parametros de rerank solo se justifica si
el A/B report muestra una relacion clara entre recall, regresiones y costo:

- aumentar candidates mejora casos `rerank_helpful` sin degradar casos
  `rerank_stable`;
- bajar candidates mantiene hit rate y reduce costo/latencia;
- el cambio conserva errores estables cuando el limite es invalido.

No cambiar defaults por una sola suite pequena. El PR debe mantener defaults
actuales salvo que el change de decision declare evidencia suficiente para
promoverlos.

## No-go inmediato

El experimento debe rechazarse o volver a diseno si ocurre cualquiera de estos
casos:

- pierde expected evidence en casos `metadata_filter` o citations;
- oculta regresiones solo porque el agregado mejora;
- requiere credenciales live para gates obligatorios;
- no puede explicar costo/latencia adicional;
- cambia dense default sin flag, migration plan o rollback;
- duplica responsabilidades de `RetrievalService` fuera de una abstraccion
  pequena y testeable.

## PR body esperado

Un PR experimental de retrieval debe incluir:

- comando exacto de eval usado;
- resumen de `comparison_metrics`;
- tabla corta de `comparison_cases` con regresiones primero;
- costo/latencia si hay provider hosted o nuevo scoring;
- decision final: proceed, hold, no-go o needs-more-data.
