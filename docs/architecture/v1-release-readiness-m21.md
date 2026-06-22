# M21 V1 release readiness

Estado: activo en planificacion.

## Decision

M21 debe avanzar como un milestone de readiness de release, no como una feature
nueva de runtime. El objetivo es convertir el core completado en M1-M20 en una
v1.0 publicable y demostrable, con alcance explicito y deferrals auditable.

La decision recomendada es recortar v1.0 al vertical slice ya demostrable y
exigir evidencia nueva para reabrir lexical/RRF, Qwen sparse retrieval, graph
defaults, voz, MCP server, auth multi-user o PDF/Office.

## Alcance recomendado

- Reconciliar `docs/architecture/v1-design.md` contra M1-M20.
- Clasificar cada item de release como `in_v1`, `defer_post_v1` o `blocked`.
- Mantener dense retrieval como default de release.
- Mantener rerank Qwen como opt-in medible.
- Mantener graph retrieval como opt-in y `hold_default`.
- Definir el paquete local de release: API, worker y Postgres/pgvector.
- Definir demo script, README y reporte reproducible de evals/costo/latencia.
- Cerrar con quality gate y OpenSpec archive.

## Fuera de alcance

- Implementar sparse retrieval, lexical full-text/RRF o nuevos defaults.
- Promover Neo4j/graph retrieval.
- Agregar auth multi-user, PDF/Office, voz, MCP server o hosted observability.
- Crear tag/release automatico sin instruccion explicita.
- Mezclar runtime features dentro del PR de planificacion.

## Secuencia

1. `m21-v1-release-readiness-plan`: crear este change OpenSpec y declarar la
   direccion.
2. `m21-v1-scope-reconciliation`: actualizar `v1-design.md` y docs para que
   el release scope coincida con OpenSpec y M1-M20.
3. `m21-release-package-local-stack`: preparar Docker Compose/runbook local con
   API, worker y Postgres/pgvector.
4. `m21-portfolio-demo-and-report`: agregar demo/readme/reporte reproducible
   para portafolio.
5. `m21-release-quality-gate`: validar, archivar M21 y dejar v1.0 listo para
   tag manual.

## Criterio de cierre

M21 debe cerrar cuando el repo pueda demostrar v1.0 local-first con un alcance
cerrado, docs coherentes, release package reproducible, reporte de evidencia y
sin changes OpenSpec activos.
