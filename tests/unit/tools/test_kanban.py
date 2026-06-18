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
