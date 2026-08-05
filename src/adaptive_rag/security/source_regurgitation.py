"""Redact long near-verbatim regurgitation of retrieved source chunks.

Parity intent with beflow-graph-rag's answer-side source filter, adapted for
RAG chunk text (not GitHub code dumps): when a chat answer contains a long
contiguous span that also appears in a retrieved chunk snippet, replace that
span with a stable marker.

Design choices (deterministic, no LLM):

- Match is exact contiguous substring (longest common substring spans), not
  bag-of-words or semantic similarity — paraphrases pass.
- Default threshold is conservative (200 characters) so short quotes and
  normal grounded answers are left alone.
- Empty source list or short chunks are a no-op passthrough.
- Answer/source lengths and source count are capped so the O(n*m) LCS DP
  cannot CPU-spike on oversized model outputs or retrieval payloads.
"""

from __future__ import annotations

from collections.abc import Sequence

REGURGITATION_MARKER = "[source excerpt redacted]"

# Spans shorter than this never count as regurgitation.
DEFAULT_MIN_SPAN_CHARS = 200

# Bounds for the classic LCS-substring DP (O(n*m) per source).
MAX_ANSWER_CHARS = 16_000
MAX_SOURCE_CHARS = 8_000
MAX_SOURCE_TEXTS = 20


def find_regurgitation_spans(
    answer: str,
    source_texts: Sequence[str],
    *,
    min_span_chars: int = DEFAULT_MIN_SPAN_CHARS,
) -> list[tuple[int, int]]:
    """Return merged ``[start, end)`` spans in ``answer`` that copy a source.

    A span is reported only when a contiguous substring of length
    ``min_span_chars`` or more appears in both the answer and at least one
    source text.

    Matching considers at most the first ``MAX_ANSWER_CHARS`` of ``answer``,
    the first ``MAX_SOURCE_TEXTS`` sources, and the first ``MAX_SOURCE_CHARS``
    of each source, so DP cost stays bounded.
    """

    if not answer or not source_texts or min_span_chars <= 0:
        return []
    # Early exit: nothing as long as the threshold can exist in the answer.
    if len(answer) < min_span_chars:
        return []

    answer_window = answer[:MAX_ANSWER_CHARS]
    if len(answer_window) < min_span_chars:
        return []

    raw: list[tuple[int, int]] = []
    for source in source_texts[:MAX_SOURCE_TEXTS]:
        if not source:
            continue
        source_window = source[:MAX_SOURCE_CHARS]
        if len(source_window) < min_span_chars:
            continue
        raw.extend(
            _longest_common_substring_spans(
                answer_window,
                source_window,
                min_span_chars=min_span_chars,
            )
        )
    return _merge_spans(raw)


def filter_source_regurgitation(
    answer: str,
    source_texts: Sequence[str],
    *,
    min_span_chars: int = DEFAULT_MIN_SPAN_CHARS,
    marker: str = REGURGITATION_MARKER,
) -> tuple[str, int]:
    """Replace regurgitated source spans with ``marker``.

    Returns ``(cleaned_answer, redaction_count)``. Clean answers are returned
    unchanged with count ``0``.
    """

    spans = find_regurgitation_spans(
        answer,
        source_texts,
        min_span_chars=min_span_chars,
    )
    if not spans:
        return answer, 0

    parts: list[str] = []
    cursor = 0
    for start, end in spans:
        parts.append(answer[cursor:start])
        parts.append(marker)
        cursor = end
    parts.append(answer[cursor:])
    return "".join(parts), len(spans)


def _longest_common_substring_spans(
    answer: str,
    source: str,
    *,
    min_span_chars: int,
) -> list[tuple[int, int]]:
    """Collect answer spans that match a contiguous source substring.

    Uses classic LCS-substring DP (length of match ending at each pair of
    indices). Every ending position whose match length is ``>= min_span`` is
    recorded; callers merge to maximal ranges.
    """

    n = len(answer)
    m = len(source)
    spans: list[tuple[int, int]] = []
    # prev[j] = length of match ending at answer[i-1], source[j-1]
    prev = [0] * (m + 1)
    for i in range(1, n + 1):
        curr = [0] * (m + 1)
        a_ch = answer[i - 1]
        for j in range(1, m + 1):
            if a_ch == source[j - 1]:
                length = prev[j - 1] + 1
                curr[j] = length
                if length >= min_span_chars:
                    spans.append((i - length, i))
        prev = curr
    return spans


def _merge_spans(spans: list[tuple[int, int]]) -> list[tuple[int, int]]:
    """Merge overlapping or adjacent ``[start, end)`` ranges."""

    if not spans:
        return []
    ordered = sorted(spans, key=lambda item: (item[0], item[1]))
    merged: list[tuple[int, int]] = [ordered[0]]
    for start, end in ordered[1:]:
        prev_start, prev_end = merged[-1]
        if start <= prev_end:
            merged[-1] = (prev_start, max(prev_end, end))
        else:
            merged.append((start, end))
    return merged


__all__ = [
    "DEFAULT_MIN_SPAN_CHARS",
    "MAX_ANSWER_CHARS",
    "MAX_SOURCE_CHARS",
    "MAX_SOURCE_TEXTS",
    "REGURGITATION_MARKER",
    "filter_source_regurgitation",
    "find_regurgitation_spans",
]
