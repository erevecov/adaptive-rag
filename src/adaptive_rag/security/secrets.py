"""Heuristic secret detection and redaction for content/output guards."""

from __future__ import annotations

import re
from re import Pattern

REDACTION_MARKER = "[REDACTED_SECRET]"

# Order matters only for overlapping spans; longer/more specific first where needed.
_SECRET_PATTERNS: tuple[Pattern[str], ...] = (
    re.compile(
        r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----"
        r"[\s\S]*?"
        r"-----END (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----"
    ),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"\bASIA[0-9A-Z]{16}\b"),
    re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}\b"),
    re.compile(r"\bghp_[A-Za-z0-9]{20,}\b"),
    re.compile(r"\bgho_[A-Za-z0-9]{20,}\b"),
    re.compile(r"\bghu_[A-Za-z0-9]{20,}\b"),
    re.compile(r"\bghs_[A-Za-z0-9]{20,}\b"),
    re.compile(r"\bghr_[A-Za-z0-9]{20,}\b"),
    # OpenAI-style and similar sk- project keys (avoid matching short words).
    re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{20,}\b"),
    re.compile(r"(?i)\bbearer\s+[A-Za-z0-9\-._~+/]+=*\b"),
)


def find_secret_spans(text: str) -> list[tuple[int, int]]:
    """Return non-overlapping (start, end) spans of secret-like matches."""

    spans: list[tuple[int, int]] = []
    for pattern in _SECRET_PATTERNS:
        for match in pattern.finditer(text):
            spans.append((match.start(), match.end()))
    if not spans:
        return []
    spans.sort(key=lambda item: (item[0], -item[1]))
    merged: list[tuple[int, int]] = []
    for start, end in spans:
        if not merged or start >= merged[-1][1]:
            merged.append((start, end))
            continue
        prev_start, prev_end = merged[-1]
        if start < prev_end:
            merged[-1] = (prev_start, max(prev_end, end))
    return merged


def redact_secrets(text: str) -> tuple[str, int]:
    """Replace secret-like spans with a stable marker.

    Returns ``(redacted_text, redaction_count)``. Clean text is returned
    unchanged with count ``0``.
    """

    spans = find_secret_spans(text)
    if not spans:
        return text, 0
    parts: list[str] = []
    cursor = 0
    for start, end in spans:
        parts.append(text[cursor:start])
        parts.append(REDACTION_MARKER)
        cursor = end
    parts.append(text[cursor:])
    return "".join(parts), len(spans)
