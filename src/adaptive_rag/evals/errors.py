"""Errores estables del contrato de evals."""

from __future__ import annotations


class EvalDatasetError(ValueError):
    """Error no retryable al cargar o validar fixtures de evals."""


class EvalConfigurationError(ValueError):
    """Error estable de configuracion para ejecuciones de evals."""
