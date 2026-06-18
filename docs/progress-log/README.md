# Registro de progreso operativo

Este directorio es append-only y no reemplaza OpenSpec, PRs ni git.

Usar un archivo por evento relevante solo cuando aporte contexto que no queda
claro en otra fuente de verdad:

- blockers externos o validados
- auditorias con evidencia concreta
- handoffs no triviales entre sesiones
- decisiones operativas que afectan el siguiente trabajo

```text
YYYY-MM-DD-short-description.md
```

Reglas:

- No registrar cierres rutinarios si el PR body y OpenSpec archive ya contienen
  la evidencia.
- No editar entradas antiguas salvo para corregir un error factual en la misma
  sesion.
- Mantener entradas concisas: contexto, evidencia, decision y siguiente paso.
