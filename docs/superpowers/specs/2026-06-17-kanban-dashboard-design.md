# Design: Kanban dashboard de solo lectura

Fecha: 2026-06-17
Estado: aprobado para plan de implementacion

## Resumen

Un kanban de solo lectura que muestra el estado de los slices del proyecto,
derivado automaticamente de los markdown que ya se mantienen. No es una
herramienta de edicion: el estado se mueve marcando checkboxes en `tasks.md`,
y el tablero lo refleja al regenerar.

El estado de las tareas vive en:

- `openspec/changes/<id>/tasks.md` - checkboxes `[ ]` / `[x]` por change.
- `openspec/changes/archive/` - cambios ya cerrados.
- `docs/roadmap.md` - secuencia de slices por milestone.

## Objetivos

- Mostrar el estado actual de cada slice del proyecto en un tablero visual.
- Derivar el estado unicamente de los markdown existentes. Cero duplicacion.
- Funcionar identico en Windows, Linux y Mac sin dependencias externas.
- Regenerar bajo demanda con un unico comando.

## No objetivos (YAGNI)

- Sin servidor HTTP.
- Sin watcher de archivos ni auto-refresh.
- Sin edicion desde la UI.
- Sin dependencias externas (solo stdlib Python + HTML/CSS/JS vainilla).
- Sin fuente de verdad secundaria (no se lee `docs/progress-log/` ni git).

## Uso

```
uv run python tools/kanban.py
```

Lee los markdown del repo, genera `tools/kanban/index.html` y lo abre en el
navegador por defecto. Funciona desde cualquier directorio de invocacion.

Pega conocida y aceptada: si se mueven checkboxes y se hace F5 sin re-correr
el script, se ven datos stale. Convencion: abrir el kanban siempre desde el
comando, no desde un bookmark al HTML.

## Arquitectura

Tres unidades aisladas en un unico archivo `tools/kanban.py` (~150 lineas):

### Parser (`parse_state(repo_root) -> dict`)

Lee markdown del proyecto y devuelve una estructura de datos con todos los
slices y su estado.

- Lee `docs/roadmap.md` para la lista de slices esperados por milestone.
- Lee `openspec/changes/*/tasks.md` para el conteo de checkboxes.
- Lee `openspec/changes/archive/*` para los cambios ya cerrados.
- Depende solo de `pathlib` + `re` del stdlib.

### Renderer HTML (`render_html(state, out_path)`)

Toma el estado parseado y genera `tools/kanban/index.html` autonomico:

- CSS inline en un `<style>` (estilo con barras de progreso y color por estado).
- JSON del estado embebido como `window.__KANBAN_STATE__` en un `<script>`. Sin
  `fetch`, sin archivo externo, funciona abriendo con `file://`.
- JS vainilla (~30 lineas) que agrupa los slices por `column` y los inyecta.
- Depende solo del modulo `html` del stdlib para escaping.

### Launcher (`main() -> int`)

Orquesta: parsear -> renderizar -> abrir navegador.

- Detecta el `repo_root` relativo a la ubicacion del script
  (`tools/kanban.py` -> `parents[1]`).
- Crea `tools/kanban/` si no existe.
- Usa `webbrowser.open(path.as_uri())` para abrir el browser de forma portable
  (usa `start` / `xdg-open` / `open` segun plataforma).
- Exit code 0 al exito; errores de parsing a stderr y exit 1.

## Estructura de archivos

```
tools/
  kanban.py              <- parser + renderer + launcher (se commitea)
  kanban/
    index.html           <- output regenerable (no se commitea, va al .gitignore)
```

## Modelo de datos

`parse_state` devuelve. (Nota: el ejemplo muestra la forma del dato; la
presencia de `m1` en `milestones` depende de que M1 este archivado - ver
"Hechos historicos".)

```python
{
  "generated_at": "2026-06-17T12:00:00",
  "milestones": [
    {"id": "m1", "title": "M1 Foundation", "closed_at": "2026-06-17"},
    {"id": "m2", "title": "M2 Dominio y persistencia", "closed_at": None},
  ],
  "slices": [
    {
      "id": "m2-domain-schema",
      "milestone_id": "m2",
      "milestone_title": "M2 Dominio y persistencia",
      "title": "domain schema",
      "column": "planned",
      "total": 18,
      "done": 0,
      "has_spec": True,
      "order": 1,
    },
  ],
}
```

## Reglas de clasificacion

Evaluadas en orden, la primera que matchea gana:

| Condicion | Columna |
|---|---|
| En `openspec/changes/archive/` o todos los checkboxes `[x]` | `done` |
| Tiene carpeta en `openspec/changes/` con `tasks.md` y `done > 0` (no todos) | `in_progress` |
| Tiene carpeta en `openspec/changes/` con `tasks.md` y `done == 0` | `planned` |
| Listado en `docs/roadmap.md` pero sin carpeta | `backlog` |

## Casos limite

- **Slice sin `tasks.md` todavia** (carpeta creada pero vacia): se trata como
  `planned` con `total=0, done=0`. La card muestra "sin tareas".
- **Slice en roadmap y en archive a la vez**: gana `done` (archive es
  definitivo). Evita que un slice cerrado aparezca duplicado en backlog.
- **Change sin proposal/design, solo tasks.md**: funciona; el parser solo lee
  `tasks.md` para el conteo.
- **Slice cerrado pero no archivado** (ej. M1 hoy): no aparece en Done hasta
  que se archive en `openspec/changes/archive/`. Esto alinea con el flujo
  OpenSpec, que prescribe archivar un change al cerrarlo.

## Parsing de markdown

### Slices esperados y orden (desde `docs/roadmap.md`)

El roadmap tiene esta estructura:

```markdown
## M2 Dominio y persistencia

Secuencia recomendada:

1. `m2-domain-schema`: modelos SQLAlchemy y migracion Alembic...
2. `m2-repositories`: capa de repositories...
```

Patron regex por linea de la lista numerada:

```
^\d+\.\s+`([^`]+)`:\s*(.+)$
```

- Grupo 1 -> `id` del slice (`m2-domain-schema`).
- Grupo 2 -> `title` descriptivo (recortado al primer `.` o salto).

El milestone se identifica con `^## (M\d+) (.+)$`
-> `milestone_id="m2"`, `milestone_title="M2 Dominio y persistencia"`.

### Conteo de checkboxes (desde `openspec/changes/<id>/tasks.md`)

- `total` = lineas que matchean `^\s*-\s*\[[ xX]\]\s+\S`.
- `done` = lineas que matchean `^\s*-\s*\[[xX]\]\s+\S`.

### Hechos historicos (desde `openspec/changes/archive/`)

Si `archive/` existe, se listan sus subdirectorios. Cada uno se trata como un
slice `done`. Si `archive/` esta vacio (como hoy), la columna Done queda vacia.

El `milestone_id` de un slice archivado se infiere del prefijo del nombre del
directorio (`archive/2026-06-17-m1-foundation/` -> `milestone_id="m1"`). El
`milestone_title` se busca en `docs/roadmap.md` si existe una seccion `## M1`;
si no, se deja el id en crudo.

### Deteccion de `has_spec`

`has_spec = (openspec/changes/<id>/tasks.md).exists()`.

## Renderer HTML

Layout del `index.html`:

- Header con titulo "Adaptive RAG - Kanban" y timestamp de generacion.
- 4 columnas horizontales: Backlog - Planificado - En progreso - Hecho. Cada
  una con un contador (`Backlog - 4`).
- Cada card: borde izquierdo con color de estado, titulo del slice, subtitulo
  con el milestone, barra de progreso (ancho = `done/total * 100%`), texto
  `done/total - estado`. Cards `done` con opacidad 0.75 y sin barra.
- Columna vacia muestra "vacio" en cursiva gris.
- Scroll horizontal si las columnas no caben.

Colores por columna:

- Backlog -> gris (`#999`).
- Planificado -> azul (`#6b8afd`).
- En progreso -> amber (`#e8a33d`).
- Hecho -> verde (`#3daf6b`).

Todo texto dinamico pasa por `html.escape()` antes de inyectarse.

## .gitignore

Anadir:

```
tools/kanban/index.html
```

El HTML es output regenerable, no se commitea. `kanban.py` si se commitea.

## Resultado esperado del parser hoy

Estado actual del repo (M1 cerrado en `docs/progress.md` pero no archivado en
`openspec/changes/archive/`):

| Slice | Columna | total/done |
|---|---|---|
| m2-domain-schema | planned | 0/18 |
| m2-repositories | backlog | sin spec |
| m2-job-queue | backlog | sin spec |
| m2-url-fetch-policy | backlog | sin spec |
| m2-quality-gate | backlog | sin spec |

La columna Done queda vacia hasta que M1 se archive, lo cual es consistente con
el flujo OpenSpec.

## Testing

- Tests unitarios sobre `parse_state` con fixtures de markdown temporales
  (mini-repo con un roadmap, un change y un archive).
- Cubrir las 4 reglas de clasificacion y los casos limite.
- El renderer se valida con un smoke test: dado un `state` fijo, el HTML
  generado contiene los IDs esperados y el JSON embebido parsea.
- El launcher (`main`) no se testa directamente; su logica portable es
  trivial y delega en `webbrowser` (stdlib).

Tests en `tests/unit/tools/test_kanban.py`, corren con `uv run pytest`.
