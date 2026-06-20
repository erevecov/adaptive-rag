# Expansion de evidencia de retrieval M12

Fecha: 2026-06-20
Estado: M12 activo

## Decision

La siguiente prioridad despues de M11 es ampliar evidencia de retrieval antes de
agregar algoritmos o defaults nuevos.

Estado por opcion:

| Opcion | Estado | Motivo |
| --- | --- | --- |
| Expansion de evidencia | `proceed` | M11 dejo una regresion distractor y cobertura insuficiente para decidir lexical/RRF o sparse. |
| Lexical/RRF | `hold` | Requiere fallos lexicales versionados y diseno de fusion con filtros/citations. |
| Qwen sparse retrieval | `hold` | Requiere docs provider actuales, storage/reindex, costo y un gap que lexical/rerank no cubra. |
| Presets/defaults de candidate tuning | `hold` | `candidate_limit=8` mejoro el agregado offline, pero degrado un caso distractor. |

## Evidencia usada

- `docs/architecture/candidate-limit-ab-evidence.md` documento que
  `candidate_limit=8` mejora el hit rate agregado, pero conserva la regresion
  `distractor-alpha-release-notes`.
- `docs/architecture/retrieval-decision-gates.md` exige leer regresiones por
  caso, costo/latencia, filtros y citations antes de abrir retrieval productivo.
- `openspec/specs/retrieval-quality/spec.md` ya exige que lexical/RRF cite
  fallos lexicales medidos y que sparse retrieval verifique docs provider
  actuales.

## Alcance M12

M12 debe producir evidencia, no algoritmos:

- taxonomia estricta para casos de riesgo;
- dataset pack ampliado con distractors y lexical misses;
- reporte de gaps por caso, con regresiones primero;
- decision matrix actualizada para lexical/RRF, sparse retrieval y candidate
  tuning.

## Familias de riesgo

La ampliacion debe cubrir:

- `semantic_distractor`: evidencia cercana semantica que no contiene el
  contrato esperado;
- `identifier_exact`: codigos, rutas, modelos, errores o nombres que requieren
  match exacto;
- `metadata_guard`: casos donde filtros excluyen evidencia tentadora;
- `multi_evidence`: respuestas que necesitan varias citas;
- `rerank_regression`: casos donde rerank desplaza evidencia correcta.

Estas familias se representan con `case_metadata.risk_family`, un campo
opcional y estricto. Suites antiguas sin ese campo quedan agrupadas como
`uncategorized` en matrices de evaluacion.

## No-go inmediato

M12 debe volver a diseno o mantener `hold` si:

- la mejora agregada oculta regresiones en distractors, metadata filters o
  multi-evidence;
- un cambio requiere credenciales live para el gate obligatorio;
- lexical/RRF se propone sin casos versionados donde dense/rerank fallen por
  terminos exactos;
- sparse retrieval se propone sin docs actuales, costo, storage y reindex;
- algun slice cambia dense retrieval como default.

## Siguiente slice

El siguiente slice recomendado es `m12-quality-gate`: validar el milestone
completo, archivar el change y publicar la spec canonica.

## Dataset pack M12

`evals/fixtures/retrieval-dataset-pack.json` ahora cubre:

- 16 evidencias versionadas;
- 10 casos de retrieval;
- lexical misses para modelo Qwen rerank y ruta exacta de export admin;
- distractor semantico para cuota realtime y visibilidad de modelo;
- `risk_family` en cada caso para agrupar evidencia de decision.

## Gap reporting M12

El reporte A/B de candidate limits ahora expone:

- `outcome_counts_by_intent`;
- `outcome_counts_by_difficulty`;
- `outcome_counts_by_risk_family`;
- `comparison_cases` serializados con regresiones primero, luego mejoras y
  empates.

## Decision refresh M12

La decision actualizada queda documentada en
`docs/architecture/retrieval-strategy-refresh-m12.md`.

Resumen:

- dense baseline pasa 10/10 casos en la suite ampliada;
- candidate limits `3`, `5` y `8` mantienen hit rate 1.0 pero introducen una
  regresion de ranking en `distractor-realtime-quota-code`;
- lexical/RRF queda en `hold` porque los lexical misses versionados no fallan
  con el baseline determinista;
- Qwen sparse queda en `hold` porque falta gap medido y docs provider actuales;
- dense retrieval sigue como default.
