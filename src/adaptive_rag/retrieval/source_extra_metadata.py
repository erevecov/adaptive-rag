"""Sanitize source.extra_metadata before citation / retrieval surfaces.

Source rows store full bodies under ``content`` / ``content_base64`` for
ingestion. Those must never be copied into retrieval citations, tool JSON,
API responses, or audit ``citation_json``.
"""

from __future__ import annotations

from typing import Any

# Bulk payload keys stored on Source.extra_metadata for authoring/ingestion.
# Denylist is intentional: safe display keys (title, filename, url, …) vary
# by source type and must pass through without an allowlist maintenance burden.
CITATION_SOURCE_EXTRA_METADATA_DENYLIST: frozenset[str] = frozenset(
    {
        "content",
        "content_base64",
    }
)


def sanitize_source_extra_metadata(
    value: dict[str, Any] | None,
) -> dict[str, Any] | None:
    """Return a shallow copy of metadata with bulk body keys removed.

    ``None`` stays ``None``. Empty dict after filtering stays empty dict so
    callers can distinguish "no metadata" from "metadata was only bulk".
    """
    if value is None:
        return None
    return {
        key: item
        for key, item in value.items()
        if key not in CITATION_SOURCE_EXTRA_METADATA_DENYLIST
    }
