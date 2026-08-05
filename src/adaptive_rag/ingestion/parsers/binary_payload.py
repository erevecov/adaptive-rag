"""Helpers for base64 binary source payloads (PDF/DOCX)."""

from __future__ import annotations

import base64
import binascii
from typing import Final

from adaptive_rag.ingestion.types import IngestionPipelineError

# Align with URLFetchPolicy.max_response_bytes (5 MiB decoded).
MAX_BINARY_SOURCE_BYTES: Final[int] = 5 * 1024 * 1024


def decode_content_base64(
    raw: object,
    *,
    max_bytes: int = MAX_BINARY_SOURCE_BYTES,
    empty_message: str = "binary source requires extra_metadata.content_base64",
) -> bytes:
    """Decode standard base64 payload; reject missing/invalid/oversize values."""

    if not isinstance(raw, str) or raw.strip() == "":
        raise IngestionPipelineError(empty_message)
    try:
        decoded = base64.b64decode(raw, validate=False)
    except (binascii.Error, ValueError) as exc:
        raise IngestionPipelineError(
            "extra_metadata.content_base64 is not valid base64"
        ) from exc
    if not decoded:
        raise IngestionPipelineError(empty_message)
    if len(decoded) > max_bytes:
        raise IngestionPipelineError(
            f"binary source exceeds max decoded size of {max_bytes} bytes"
        )
    return decoded
