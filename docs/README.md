# Documentacion del proyecto

Este repo mantiene pocas fuentes de verdad para evitar duplicar estado entre
planes, specs, PRs y bitacoras.

## Fuentes de verdad

- `openspec/specs/`: contratos canonicos ya aceptados. Si una spec canonica
  contradice documentacion historica, manda OpenSpec.
- `openspec/changes/`: cambios activos con propuesta, diseno, tareas y delta
  specs.
- `openspec/changes/archive/`: historial formal de changes cerrados despues de
  sincronizar specs canonicas.
- `docs/architecture/`: lineas base de arquitectura y decisiones de producto de
  largo plazo. No se usa para tracking de tareas.
- `docs/roadmap.md`: orden macro de milestones y slices.
- `docs/progress.md`: handoff corto del estado actual y siguiente paso.
- `docs/progress-log/`: entradas append-only solo para blockers, auditorias,
  handoffs no triviales o evidencia que no quede clara en OpenSpec, PR o git.

## Reglas

- No crear nuevos planes o specs bajo `docs/superpowers/`.
- Para comportamiento nuevo o cambios de contrato, crear un change OpenSpec.
- Para arquitectura transversal que no sea un change ejecutable, usar
  `docs/architecture/`.
- Para cierres rutinarios, preferir OpenSpec archive + PR body. No duplicar el
  mismo cierre en `docs/progress-log/` salvo que agregue contexto operativo real.
- Mantener `docs/progress.md` breve. Debe responder "donde estamos" y "que
  sigue", no duplicar tareas completas.
