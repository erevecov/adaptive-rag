"""Strip fabricated ``[doc-N]`` / ``[self-N]`` markers from chat answers.

Parity target: beflow-graph-rag ``backend/src/rag/citation_filter.py``.
Adaptive already validates structured citation chunk_ids against retrieval;
this filter is the text-level safety net when a model still emits bracket
markers in free text (including decorated forms like ``[doc-1 (story)]``).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

_MARKER_RE = re.compile(r"\[(doc|self)-(\d+)(\s+[^\]]*)?\]")


@dataclass
class CitationMarkerFilter:
    """Stateful streaming filter for ``[doc-N]`` / ``[self-N]`` markers."""

    max_doc: int
    max_self: int = 0
    _pending: str = ""
    fabricated: list[str] = field(default_factory=list)

    def push(self, chunk: str) -> str:
        buf = self._pending + chunk
        self._pending = ""
        out: list[str] = []
        i = 0
        while i < len(buf):
            bracket = buf.find("[", i)
            if bracket == -1:
                out.append(buf[i:])
                break
            out.append(buf[i:bracket])
            close = buf.find("]", bracket)
            if close == -1:
                self._pending = buf[bracket:]
                return "".join(out)
            candidate = buf[bracket : close + 1]
            match = _MARKER_RE.fullmatch(candidate)
            if match is None:
                out.append(candidate)
            else:
                namespace, n_str, trailing = (
                    match.group(1),
                    match.group(2),
                    match.group(3),
                )
                n = int(n_str)
                limit = self.max_doc if namespace == "doc" else self.max_self
                if 1 <= n <= limit:
                    if trailing:
                        self.fabricated.append(candidate)
                        out.append(f"[{namespace}-{n}]")
                    else:
                        out.append(candidate)
                else:
                    self.fabricated.append(candidate)
            i = close + 1
        return "".join(out)

    def flush(self) -> str:
        pending = self._pending
        self._pending = ""
        return pending


def filter_citation_markers(
    text: str,
    *,
    max_doc: int,
    max_self: int = 0,
) -> tuple[str, list[str]]:
    """One-shot filter for a complete answer string."""

    filt = CitationMarkerFilter(max_doc=max_doc, max_self=max_self)
    body = filt.push(text)
    body += filt.flush()
    return body, list(filt.fabricated)
