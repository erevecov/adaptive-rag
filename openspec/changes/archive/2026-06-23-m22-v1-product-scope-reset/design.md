# Diseno M22 de V1 product scope reset

## Decision

v1 ya no significa "release de portafolio del core M1-M21". v1 significa
producto local-first single-user terminado.

M21 se conserva como evidencia de que el core tecnico puede correr, validarse y
empaquetarse localmente. M22 cambia el criterio de finalizacion: un usuario debe
poder crear un proyecto, agregar fuentes, ejecutar ingestion, ver estado,
preguntar sobre sus propios datos, revisar citas/observability y recuperar
errores desde superficies publicas documentadas.

## Alcance de producto v1

La v1 terminada debe incluir, como minimo:

- project/source authoring por API, CLI y UI o una alternativa publicamente
  documentada que no requiera fixtures internas;
- ingestion end-to-end desde fuente creada por el usuario hasta chunks,
  embeddings, jobs y retrieval;
- estados visibles para jobs, errores y reintentos;
- onboarding local-first con configuracion minima, migraciones, demo y datos
  propios;
- chat/retrieval principal con citations, history, streaming y observability ya
  existentes;
- documentacion que diferencie modo offline/fake, Qwen hosted opt-in y graph
  opt-in sin convertirlos en requisitos default;
- quality gate final que valide docs, OpenSpec, frontend, Python, smokes y un
  demo con datos ingresados por usuario.

## Fuera de alcance de este PR

Este PR no implementa authoring, ingestion UI, endpoints nuevos, jobs UI ni
cambios de runtime. Solo corrige la direccion documental y contractual para que
los siguientes slices no optimicen una release prematura.

## Riesgos y mitigacion

- Riesgo: M21 ya dejo docs que dicen que v1.0 puede cortarse.
  Mitigacion: progress, roadmap, README y arquitectura se actualizan para
  declarar M21 como pre-v1/core readiness.
- Riesgo: el nuevo v1 se infle con features aspiracionales.
  Mitigacion: `v1-product-completion` define bloques obligatorios y mantiene
  features como graph default, sparse, auth multi-user, voice, MCP y PDF/Office
  fuera del gate salvo nuevo OpenSpec con evidencia.
- Riesgo: el porcentaje de v1 pierda sentido.
  Mitigacion: el porcentaje debe recalcularse contra backlog de producto
  terminado, no contra checklist de release package M21.

## Secuencia recomendada despues de M22

1. `m23-product-authoring-surface`: crear/editar projects y sources desde
   API/CLI/UI con aislamiento por proyecto.
2. `m24-ingestion-ops-surface`: ingestion end-to-end y jobs visibles desde UI y
   CLI, con errores recuperables.
3. `m25-first-run-onboarding`: setup local, migraciones, seed/demo y guias para
   datos propios.
4. `m26-v1-product-quality-gate`: demo final con datos propios, docs y gate de
   release real.
