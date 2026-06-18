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
    return {
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "milestones": milestones,
        "slices": slices,
    }


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


def render_html(state: dict, out_path: Path) -> None:
    raise NotImplementedError


def main() -> int:
    raise NotImplementedError


if __name__ == "__main__":
    raise SystemExit(main())
