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
    raise NotImplementedError


def render_html(state: dict, out_path: Path) -> None:
    raise NotImplementedError


def main() -> int:
    raise NotImplementedError


if __name__ == "__main__":
    raise SystemExit(main())
