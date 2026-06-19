"""Metricas puras compartidas por runners de evals."""

from __future__ import annotations


def ratio(numerator: int, denominator: int, *, empty_value: float = 1.0) -> float:
    if denominator == 0:
        return empty_value
    return numerator / denominator


def passes_threshold(value: float, threshold: float | None) -> bool:
    return threshold is None or value >= threshold
