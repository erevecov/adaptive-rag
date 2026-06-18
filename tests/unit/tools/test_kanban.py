from __future__ import annotations

import importlib.util
import pathlib


def _load_kanban():
    """Load tools/kanban.py as a module (it's a script, not a package)."""
    here = pathlib.Path(__file__).resolve()
    repo_root = here.parents[3]
    kanban_path = repo_root / "tools" / "kanban.py"
    spec = importlib.util.spec_from_file_location("kanban", kanban_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module, repo_root


def _write(repo_root: pathlib.Path, rel: str, content: str) -> None:
    path = repo_root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_parse_state_extracts_milestones_and_ordered_slices(tmp_path):
    kanban, _ = _load_kanban()

    _write(
        tmp_path,
        "docs/roadmap.md",
        """# Roadmap

## Estado actual

## M2 Dominio y persistencia

Secuencia recomendada:

1. `m2-domain-schema`: modelos SQLAlchemy y migracion Alembic para schema de proyectos.
2. `m2-repositories`: capa de repositories con aislamiento por proyecto.
""",
    )

    state = kanban.parse_state(tmp_path)

    assert state["milestones"][0]["id"] == "m2"
    assert state["milestones"][0]["title"] == "M2 Dominio y persistencia"
    assert state["milestones"][0]["closed_at"] is None

    slice_ids = [s["id"] for s in state["slices"]]
    assert slice_ids == ["m2-domain-schema", "m2-repositories"]

    schema = next(s for s in state["slices"] if s["id"] == "m2-domain-schema")
    assert schema["milestone_id"] == "m2"
    assert schema["milestone_title"] == "M2 Dominio y persistencia"
    assert schema["order"] == 1
    assert schema["title"] == "modelos SQLAlchemy y migracion Alembic para schema de proyectos"


def test_parse_state_counts_checkboxes_from_tasks_md(tmp_path):
    kanban, _ = _load_kanban()

    _write(
        tmp_path,
        "docs/roadmap.md",
        """# Roadmap

## M2 Dominio y persistencia

1. `m2-domain-schema`: modelos y migracion.
""",
    )
    _write(
        tmp_path,
        "openspec/changes/m2-domain-schema/tasks.md",
        """# Tareas

## 1. Setup

- [ ] 1.1 Confirmar baseline.
- [x] 1.2 Crear branch.
- [x] 1.3 Validar.

## 2. Modelos

- [ ] 2.1 Tests.
""",
    )

    state = kanban.parse_state(tmp_path)

    schema = state["slices"][0]
    assert schema["has_spec"] is True
    assert schema["total"] == 4
    assert schema["done"] == 2


def test_parse_state_handles_missing_tasks_md(tmp_path):
    kanban, _ = _load_kanban()

    _write(
        tmp_path,
        "docs/roadmap.md",
        """# Roadmap

## M2 Dominio y persistencia

1. `m2-repositories`: capa de repositories.
""",
    )

    state = kanban.parse_state(tmp_path)

    repo = state["slices"][0]
    assert repo["has_spec"] is False
    assert repo["total"] == 0
    assert repo["done"] == 0


def _roadmap_with(slice_id: str) -> str:
    return (
        "# Roadmap\n\n"
        "## M2 Dominio y persistencia\n\n"
        f"1. `{slice_id}`: descripcion.\n"
    )


def test_classify_backlog_when_no_spec(tmp_path):
    kanban, _ = _load_kanban()
    _write(tmp_path, "docs/roadmap.md", _roadmap_with("m2-no-spec"))
    state = kanban.parse_state(tmp_path)
    assert state["slices"][0]["column"] == "backlog"


def test_classify_planned_when_spec_with_zero_done(tmp_path):
    kanban, _ = _load_kanban()
    _write(tmp_path, "docs/roadmap.md", _roadmap_with("m2-domain-schema"))
    _write(
        tmp_path,
        "openspec/changes/m2-domain-schema/tasks.md",
        "# Tareas\n\n- [ ] 1.1 Pendiente.\n- [ ] 1.2 Pendiente.\n",
    )
    state = kanban.parse_state(tmp_path)
    assert state["slices"][0]["column"] == "planned"


def test_classify_in_progress_when_partial_done(tmp_path):
    kanban, _ = _load_kanban()
    _write(tmp_path, "docs/roadmap.md", _roadmap_with("m2-domain-schema"))
    _write(
        tmp_path,
        "openspec/changes/m2-domain-schema/tasks.md",
        "# Tareas\n\n- [ ] 1.1 Pendiente.\n- [x] 1.2 Hecho.\n",
    )
    state = kanban.parse_state(tmp_path)
    assert state["slices"][0]["column"] == "in_progress"


def test_classify_done_when_all_checked(tmp_path):
    kanban, _ = _load_kanban()
    _write(tmp_path, "docs/roadmap.md", _roadmap_with("m2-domain-schema"))
    _write(
        tmp_path,
        "openspec/changes/m2-domain-schema/tasks.md",
        "# Tareas\n\n- [x] 1.1 Hecho.\n- [x] 1.2 Hecho.\n",
    )
    state = kanban.parse_state(tmp_path)
    assert state["slices"][0]["column"] == "done"


def test_classify_done_when_archived_even_without_roadmap(tmp_path):
    kanban, _ = _load_kanban()
    _write(
        tmp_path,
        "docs/roadmap.md",
        "# Roadmap\n\n## M2 Dominio y persistencia\n\n1. `m2-next`: siguiente.\n",
    )
    _write(
        tmp_path,
        "openspec/changes/archive/2026-06-17-m1-foundation/tasks.md",
        "# Tareas\n\n- [x] 1.1 Hecho.\n",
    )
    state = kanban.parse_state(tmp_path)

    archived = [s for s in state["slices"] if s["id"] == "m1-foundation"]
    assert len(archived) == 1
    assert archived[0]["column"] == "done"
    assert archived[0]["milestone_id"] == "m1"


def test_classify_archived_wins_over_roadmap_duplicate(tmp_path):
    """A slice listed in roadmap AND archived appears once, as done."""
    kanban, _ = _load_kanban()
    _write(
        tmp_path,
        "docs/roadmap.md",
        "# Roadmap\n\n## M2 Dominio y persistencia\n\n1. `m1-foundation`: base.\n",
    )
    _write(
        tmp_path,
        "openspec/changes/archive/2026-06-17-m1-foundation/tasks.md",
        "# Tareas\n\n- [x] 1.1 Hecho.\n",
    )
    state = kanban.parse_state(tmp_path)

    matches = [s for s in state["slices"] if s["id"] == "m1-foundation"]
    assert len(matches) == 1
    assert matches[0]["column"] == "done"


def test_render_html_embeds_state_and_slices(tmp_path):
    kanban, _ = _load_kanban()

    state = {
        "generated_at": "2026-06-17T12:00:00+00:00",
        "milestones": [{"id": "m2", "title": "M2 Dominio y persistencia", "closed_at": None}],
        "slices": [
            {
                "id": "m2-domain-schema",
                "milestone_id": "m2",
                "milestone_title": "M2 Dominio y persistencia",
                "title": "modelos y migracion",
                "column": "planned",
                "total": 18,
                "done": 0,
                "has_spec": True,
                "order": 1,
            }
        ],
    }

    out_path = tmp_path / "index.html"
    kanban.render_html(state, out_path)

    content = out_path.read_text(encoding="utf-8")
    # State is embedded as JSON.
    assert "window.__KANBAN_STATE__" in content
    # Slice id and title appear.
    assert "m2-domain-schema" in content
    assert "modelos y migracion" in content
    # All four column headers are present.
    for header in ("Backlog", "Planificado", "En progreso", "Hecho"):
        assert header in content
    # It is a standalone HTML doc.
    assert content.lstrip().startswith("<!DOCTYPE html>")
