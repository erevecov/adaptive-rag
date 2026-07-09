"""Helpers compartidos para traducir errores de dominio a HTTPException."""

from __future__ import annotations

from fastapi import HTTPException

from adaptive_rag.errors import DomainError


def domain_http_error(error: DomainError) -> HTTPException:
    return HTTPException(status_code=error.status_code, detail=error.detail)
