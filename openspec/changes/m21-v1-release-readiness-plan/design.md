# Diseno M21 de V1 release readiness

## Contexto

El repo esta en un punto distinto al del diseno v1 original. El documento base
de v1 buscaba una primera release publica con:

- crear proyectos;
- agregar fuentes Markdown, TXT y URL HTML publica;
- indexarlas;
- ejecutar retrieval hibrido;
- chatear con citations;
- correr evals;
- mostrar un reporte reproducible de calidad/costo/latencia.

M1-M20 cerraron gran parte del core, pero tambien produjeron decisiones
conservadoras:

- dense retrieval sigue siendo el default;
- rerank es opt-in;
- lexical/RRF y Qwen sparse quedaron en hold hasta tener evidencia;
- Neo4j/graph retrieval sigue opt-in y `hold_default`;
- el frontend existe, aunque el diseno v1 original decia que un frontend
  completo quedaba fuera de la primera release.

M21 debe reconciliar esa realidad. El objetivo no es implementar otra feature
grande, sino fijar el corte de v1.0 y producir un plan final pequeno.

## Opciones evaluadas

### Opcion A: mantener el v1-design original como contrato estricto

Ventaja: evita reabrir decisiones historicas.

Costo: fuerza a construir sparse retrieval, lexical/RRF y packaging antes de
publicar, aunque M10-M12 ya dejaron esas rutas en hold por falta de evidencia.
Esto empuja el release hacia un alcance mas grande que el core ya demostrable.

### Opcion B: recortar v1.0 al core demostrable y dejar deferrals explicitos

Ventaja: convierte M1-M20 en una release de portafolio con menor blast radius.
Mantiene dense + rerank opt-in + chat + evals + observability como producto
demostrable, y exige evidencia nueva para reabrir lexical/RRF, sparse o graph
defaults.

Costo: requiere actualizar `v1-design.md` y README para admitir que algunos
items originales pasan a post-v1.

### Opcion C: etiquetar el estado actual como v1.0 sin M21

Ventaja: es rapido.

Costo: publicaria un release sin checklist, sin demo reproducible, sin README
final y sin decidir explicitamente que pasa con los items originales en hold.

## Decision

La decision recomendada es la opcion B: M21 debe ser un milestone de readiness,
no un milestone de nueva capability runtime.

V1.0 debe priorizar un vertical slice demostrable y reproducible:

- proyecto local-first;
- ingestion/indexing verificable con las rutas ya implementadas;
- retrieval dense default con citations;
- rerank Qwen opt-in y medible;
- chat con tool calling, audit trail, historial y streaming;
- observability local-first y dashboard read-only;
- evals/reportes reproducibles;
- packaging local y README/demo de portafolio.

Qwen sparse/dense_sparse, Postgres full-text/RRF, graph rollout/defaults, voz,
MCP server, auth multi-user, PDF/Office y observability hosted quedan fuera de
v1.0 salvo que un slice de scope reconciliation demuestre que alguno ya esta
cerrado sin aumentar riesgo.

## Objetivos

- Convertir el estimado post-M20 en una checklist de release verificable.
- Actualizar el alcance v1.0 para reflejar decisiones ya tomadas en M10-M20.
- Separar `in_v1`, `defer_post_v1` y `blocked` con razonamiento auditable.
- Definir los PRs finales para release package, demo, README y reporte.
- Evitar que lexical/RRF, sparse retrieval o graph defaults entren por inercia.
- Mantener cada slice posterior pequeno y mergeable.

## No objetivos

- No implementar sparse retrieval.
- No implementar lexical full-text/RRF.
- No cambiar defaults de retrieval, rerank, providers, streaming ni graph.
- No agregar auth multi-user, PDF/Office, MCP server, voz ni hosted
  observability.
- No hacer tag/release en este PR de planificacion.
- No reescribir la historia de M1-M20.

## Secuencia recomendada de M21

### 1. `m21-v1-release-readiness-plan`

Alcance:

- Crear el change OpenSpec M21.
- Documentar decision, alcance, no objetivos y slices.
- Agregar capability `v1-release-readiness`.
- Actualizar progress/roadmap y arquitectura.

Fuera de alcance:

- Codigo productivo frontend/backend.
- Docker Compose, README final o demo script ejecutable.

### 2. `m21-v1-scope-reconciliation`

Alcance:

- Revisar cada item de `docs/architecture/v1-design.md` contra M1-M20.
- Clasificar items como `in_v1`, `defer_post_v1` o `blocked`.
- Actualizar `v1-design.md` para que OpenSpec y el diseno no se contradigan.
- Confirmar explicitamente que lexical/RRF, Qwen sparse y graph defaults siguen
  fuera de v1.0 salvo evidencia nueva.

Fuera de alcance:

- Implementar esos deferrals.
- Cambiar runtime o defaults.

### 3. `m21-release-package-local-stack`

Alcance:

- Agregar o reconciliar Docker Compose para `api`, `worker` y Postgres/pgvector.
- Documentar variables minimas, `.env.example` y comandos de arranque.
- Agregar smoke local que pruebe health/API/CLI sin requerir providers hosted.

Fuera de alcance:

- Neo4j como servicio obligatorio.
- Servicios hosted o profiles avanzados.

### 4. `m21-portfolio-demo-and-report`

Alcance:

- Agregar un demo script reproducible o runbook automatizable.
- Generar o documentar un reporte de evals/costo/latencia reproducible con
  artefactos JSON.
- Actualizar README para explicar setup, demo, limites, decisiones de scope y
  screenshots/observability si aplica.

Fuera de alcance:

- Marketing site.
- Benchmarks no reproducibles o dependientes de secretos.

### 5. `m21-release-quality-gate`

Alcance:

- Ejecutar frontend/Python/OpenSpec y smokes de release.
- Verificar que no quedan changes activos.
- Archivar M21 y dejar el repo listo para tag/release manual.

Fuera de alcance:

- Crear el tag si el usuario no lo pide explicitamente.

## Criterio de cierre

M21 cierra cuando el repo tenga un alcance v1.0 explicito, una secuencia final
mergeada o lista para ejecutar, y un gate que demuestre que el release local se
puede reproducir sin servicios obligatorios fuera de Postgres/pgvector.
