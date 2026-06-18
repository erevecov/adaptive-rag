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


def render_html(state: dict, out_path: Path) -> None:
    raise NotImplementedError


def main() -> int:
    raise NotImplementedError


if __name__ == "__main__":
    raise SystemExit(main())
