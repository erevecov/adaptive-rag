"""Errores de dominio compartidos con mensaje estable para API y CLI."""

from __future__ import annotations


class DomainError(Exception):
    """Error esperado de dominio con mensaje estable y status HTTP asociado."""

    def __init__(self, detail: str, *, status_code: int) -> None:
        super().__init__(detail)
        self.detail = detail
        self.status_code = status_code
