"""Helpers for base64 binary source payloads (PDF/DOCX)."""

from __future__ import annotations

import base64
import binascii
from typing import Final

from adaptive_rag.ingestion.url_fetch_policy import URLFetchPolicy

# Align with URLFetchPolicy.max_response_bytes (5 MiB decoded).
MAX_BINARY_SOURCE_BYTES: Final[int] = URLFetchPolicy().max_response_bytes


def max_base64_encoded_chars(max_decoded_bytes: int) -> int:
    """Upper bound on base64 character count for a given decoded size.

    Standard base64 expands 3 bytes → 4 chars, with up to 2 padding chars.
    Allow a small margin for whitespace that strip() would remove.
    """

    return ((max_decoded_bytes + 2) // 3) * 4 + 64


def decode_content_base64(
    raw: object,
    *,
    max_bytes: int = MAX_BINARY_SOURCE_BYTES,
    source_type: str = "binary",
) -> bytes:
    """Decode standard base64 payload; reject missing/invalid/oversize values.

    Prefers a pre-decode length check so huge payloads fail before allocating
    the full decoded buffer.
    """

    if not isinstance(raw, str) or raw.strip() == "":
        raise ValueError(
            f"{source_type} source requires extra_metadata.content_base64"
        )
    compact = "".join(raw.split())
    if len(compact) > max_base64_encoded_chars(max_bytes):
        raise ValueError(
            f"{source_type} source exceeds max binary size of {max_bytes} bytes"
        )
    try:
        decoded = base64.b64decode(compact, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ValueError(
            f"{source_type} source content_base64 is invalid"
        ) from exc
    if not decoded:
        raise ValueError(f"{source_type} source content_base64 is empty")
    if len(decoded) > max_bytes:
        raise ValueError(
            f"{source_type} source exceeds max binary size of {max_bytes} bytes"
        )
    return decoded
