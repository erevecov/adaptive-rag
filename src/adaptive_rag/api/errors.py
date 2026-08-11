"""Stable API error helpers."""

from __future__ import annotations

from typing import Never

from fastapi import HTTPException


def raise_api_error(status_code: int, code: str, message: str | None = None) -> Never:
    detail = {"code": code}
    if message is not None:
        detail["message"] = message
    raise HTTPException(status_code=status_code, detail=detail)
