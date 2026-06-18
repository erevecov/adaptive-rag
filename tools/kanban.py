"""Read-only kanban dashboard generator.

Parses project markdown (roadmap + openspec changes + archive) into a state
dict, renders a self-contained HTML file with the state embedded as JSON, and
opens it in the default browser. Cross-platform (Windows/Linux/Mac), stdlib
only.

Usage:
    uv run python tools/kanban.py
"""

from __future__ import annotations

import html
import json
import re
import webbrowser
from datetime import datetime
from pathlib import Path


def parse_state(repo_root: Path) -> dict:
    roadmap = (repo_root / "docs" / "roadmap.md").read_text(encoding="utf-8")
    milestones = _parse_milestones(roadmap)
    slices = _parse_slices(roadmap, milestones)
    _enrich_from_changes(repo_root, slices)
    _add_archived(repo_root, slices, milestones)
    _classify_all(slices)
    return {
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "milestones": milestones,
        "slices": slices,
    }


def _enrich_from_changes(repo_root: Path, slices: list[dict]) -> None:
    for slice_ in slices:
        tasks_path = repo_root / "openspec" / "changes" / slice_["id"] / "tasks.md"
        slice_["has_spec"] = tasks_path.exists()
        total, done = _count_checkboxes(tasks_path)
        slice_["total"] = total
        slice_["done"] = done


_ARCHIVE_MILESTONE_RE = re.compile(r"^(m\d+)")


def _add_archived(repo_root: Path, slices: list[dict], milestones: list[dict]) -> None:
    archive_dir = repo_root / "openspec" / "changes" / "archive"
    if not archive_dir.is_dir():
        return
    title_by_id = {m["id"]: m["title"] for m in milestones}
    for entry in sorted(archive_dir.iterdir()):
        if not entry.is_dir():
            continue
        # Directory names look like "2026-06-17-m1-foundation" or "m1-foundation".
        slice_id = _strip_date_prefix(entry.name)
        match = _ARCHIVE_MILESTONE_RE.match(slice_id)
        if match is None:
            continue
        milestone_id = match.group(1)
        tasks_path = entry / "tasks.md"
        total, done = _count_checkboxes(tasks_path)
        # If the slice is already present (e.g. listed in roadmap), archive
        # wins: promote it to done rather than skipping.
        promoted = False
        for existing in slices:
            if existing["id"] == slice_id:
                existing["column"] = "done"
                promoted = True
                break
        if promoted:
            continue
        slices.append(
            {
                "id": slice_id,
                "milestone_id": milestone_id,
                "milestone_title": title_by_id.get(milestone_id, milestone_id),
                "title": "(archivado)",
                "column": "done",
                "total": total,
                "done": done,
                "has_spec": tasks_path.exists(),
                "order": 999,
            }
        )


def _strip_date_prefix(name: str) -> str:
    # "2026-06-17-m1-foundation" -> "m1-foundation"; "m1-foundation" -> unchanged.
    match = re.match(r"^\d{4}-\d{2}-\d{2}-(.+)$", name)
    return match.group(1) if match else name


def _classify_all(slices: list[dict]) -> None:
    for slice_ in slices:
        if slice_["column"] == "done":
            continue  # archive entries are already done
        slice_["column"] = _classify(slice_)


def _classify(slice_: dict) -> str:
    total = slice_["total"]
    done = slice_["done"]
    if total > 0 and done == total:
        return "done"
    if slice_["has_spec"] and done > 0:
        return "in_progress"
    if slice_["has_spec"]:
        return "planned"
    return "backlog"


_CHECKBOX_TOTAL_RE = re.compile(r"^\s*-\s*\[[ xX]\]\s+\S", re.MULTILINE)
_CHECKBOX_DONE_RE = re.compile(r"^\s*-\s*\[[xX]\]\s+\S", re.MULTILINE)


def _count_checkboxes(tasks_path: Path) -> tuple[int, int]:
    if not tasks_path.exists():
        return 0, 0
    text = tasks_path.read_text(encoding="utf-8")
    total = len(_CHECKBOX_TOTAL_RE.findall(text))
    done = len(_CHECKBOX_DONE_RE.findall(text))
    return total, done


_MILESTONE_RE = re.compile(r"^##\s+(M\d+)\s+(.+?)\s*$", re.MULTILINE)


def _parse_milestones(roadmap_text: str) -> list[dict]:
    milestones = []
    for match in _MILESTONE_RE.finditer(roadmap_text):
        milestones.append(
            {
                "id": match.group(1).lower(),
                "title": f"{match.group(1)} {match.group(2)}",
                "closed_at": None,
            }
        )
    return milestones


_SLICE_RE = re.compile(r"^\d+\.\s+`([^`]+)`:\s*(.+?)\s*$", re.MULTILINE)


def _parse_slices(roadmap_text: str, milestones: list[dict]) -> list[dict]:
    title_by_id = {m["id"]: m["title"] for m in milestones}
    current_milestone_id: str | None = None
    slices: list[dict] = []
    order_per_milestone: dict[str, int] = {}

    lines = roadmap_text.splitlines()
    for line in lines:
        m_header = _MILESTONE_RE.match(line)
        if m_header:
            current_milestone_id = m_header.group(1).lower()
            continue
        m_slice = _SLICE_RE.match(line)
        if m_slice and current_milestone_id is not None:
            order_per_milestone[current_milestone_id] = (
                order_per_milestone.get(current_milestone_id, 0) + 1
            )
            slices.append(
                {
                    "id": m_slice.group(1),
                    "milestone_id": current_milestone_id,
                    "milestone_title": title_by_id.get(
                        current_milestone_id, current_milestone_id
                    ),
                    "title": m_slice.group(2).rstrip("."),
                    "column": "backlog",
                    "total": 0,
                    "done": 0,
                    "has_spec": False,
                    "order": order_per_milestone[current_milestone_id],
                }
            )
    return slices


_COLUMNS = [
    ("backlog", "Backlog", "#999"),
    ("planned", "Planificado", "#6b8afd"),
    ("in_progress", "En progreso", "#e8a33d"),
    ("done", "Hecho", "#3daf6b"),
]

_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Adaptive RAG - Kanban</title>
<style>
  * {{ box-sizing: border-box; }}
  body {{ font-family: system-ui, -apple-system, Segoe UI, Roboto, sans-serif;
         margin: 0; background: #fafafa; color: #222; }}
  header {{ padding: 16px 20px; background: #fff; border-bottom: 1px solid #e5e5e5; }}
  header h1 {{ margin: 0; font-size: 18px; }}
  header .meta {{ color: #888; font-size: 12px; margin-top: 4px; }}
  .board {{ display: flex; gap: 14px; padding: 16px; overflow-x: auto; }}
  .column {{ flex: 0 0 240px; }}
  .column h2 {{ font-size: 11px; text-transform: uppercase; letter-spacing: .08em;
               margin: 0 0 10px; }}
  .column .empty {{ color: #bbb; font-style: italic; font-size: 12px; padding: 10px; }}
  .card {{ background: #fff; border: 1px solid #e5e5e5; border-radius: 6px;
           padding: 10px; margin-bottom: 8px; }}
  .card .title {{ font-weight: 600; font-size: 13px; }}
  .card .sub {{ color: #888; font-size: 11px; margin-top: 2px; }}
  .bar {{ height: 5px; background: #eee; border-radius: 3px; margin-top: 8px; overflow: hidden; }}
  .bar > span {{ display: block; height: 100%; border-radius: 3px; }}
  .card .progress-text {{ font-size: 11px; margin-top: 4px; }}
  .card.done {{ opacity: 0.75; }}
</style>
</head>
<body>
<header>
  <h1>Adaptive RAG - Kanban</h1>
  <div class="meta">Generado: {generated_at}</div>
</header>
<div class="board" id="board"></div>
<script>
window.__KANBAN_STATE__ = {state_json};
(function () {{
  var state = window.__KANBAN_STATE__;
  var columns = {columns_json};
  var board = document.getElementById("board");
  columns.forEach(function (col) {{
    var items = state.slices.filter(function (s) {{ return s.column === col.id; }});
    var colEl = document.createElement("div");
    colEl.className = "column";
    var header = document.createElement("h2");
    header.textContent = col.label + " \u00b7 " + items.length;
    header.style.color = col.color;
    colEl.appendChild(header);
    if (items.length === 0) {{
      var empty = document.createElement("div");
      empty.className = "empty";
      empty.textContent = "vacio";
      colEl.appendChild(empty);
    }}
    items.forEach(function (s) {{
      var card = document.createElement("div");
      card.className = "card " + s.column;
      card.style.borderLeft = "3px solid " + col.color;
      var title = document.createElement("div");
      title.className = "title";
      title.textContent = s.id;
      card.appendChild(title);
      var sub = document.createElement("div");
      sub.className = "sub";
      sub.textContent = s.milestone_title;
      card.appendChild(sub);
      if (s.column !== "done" && s.total > 0) {{
        var bar = document.createElement("div");
        bar.className = "bar";
        var fill = document.createElement("span");
        fill.style.width = (s.total === 0 ? 0 : Math.round(s.done / s.total * 100)) + "%";
        fill.style.background = col.color;
        bar.appendChild(fill);
        card.appendChild(bar);
      }}
      var pt = document.createElement("div");
      pt.className = "progress-text";
      pt.style.color = col.color;
      pt.textContent = s.total === 0 ? "sin tareas" : (s.done + "/" + s.total);
      card.appendChild(pt);
      colEl.appendChild(card);
    }});
    board.appendChild(colEl);
  }});
}})();
</script>
</body>
</html>
"""


def render_html(state: dict, out_path: Path) -> None:
    columns = [{"id": cid, "label": label, "color": color} for cid, label, color in _COLUMNS]
    html_doc = _HTML_TEMPLATE.format(
        generated_at=html.escape(state["generated_at"]),
        state_json=json.dumps(state, ensure_ascii=False),
        columns_json=json.dumps(columns, ensure_ascii=False),
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html_doc, encoding="utf-8")


def main() -> int:
    raise NotImplementedError


if __name__ == "__main__":
    raise SystemExit(main())
