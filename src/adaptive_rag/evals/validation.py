"""Validadores JSON reutilizables para fixtures de evals."""

from __future__ import annotations

from collections.abc import Mapping
from typing import cast

from adaptive_rag.evals.errors import EvalDatasetError

JsonMapping = Mapping[str, object]


def reject_unknown_fields(
    payload: JsonMapping,
    *,
    allowed: frozenset[str],
    field_name: str,
) -> None:
    unknown = sorted(set(payload) - allowed)
    if unknown:
        raise EvalDatasetError(
            f"{field_name} has unknown fields: {', '.join(unknown)}"
        )


def required(payload: JsonMapping, key: str, *, field_name: str) -> object:
    try:
        return payload[key]
    except KeyError as exc:
        raise EvalDatasetError(f"{field_name}.{key} is required") from exc


def expect_mapping(value: object, *, field_name: str) -> JsonMapping:
    if not isinstance(value, Mapping):
        raise EvalDatasetError(f"{field_name} must be an object")
    return cast(JsonMapping, value)


def expect_list(value: object, *, field_name: str) -> list[object]:
    if not isinstance(value, list):
        raise EvalDatasetError(f"{field_name} must be a list")
    return value


def expect_nonempty_str(value: object, *, field_name: str) -> str:
    if not isinstance(value, str):
        raise EvalDatasetError(f"{field_name} must be a string")
    normalized = value.strip()
    if not normalized:
        raise EvalDatasetError(f"{field_name} must not be empty")
    return normalized


def optional_nonempty_str(value: object, *, field_name: str) -> str | None:
    if value is None:
        return None
    return expect_nonempty_str(value, field_name=field_name)


def expect_int(value: object, *, field_name: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise EvalDatasetError(f"{field_name} must be an integer")
    return value


def optional_positive_int(
    value: object,
    *,
    default: int,
    field_name: str,
) -> int:
    if value is None:
        return default
    result = expect_int(value, field_name=field_name)
    if result <= 0:
        raise EvalDatasetError(f"{field_name} must be positive")
    return result


def optional_float(value: object, *, field_name: str) -> float | None:
    if value is None:
        return None
    return expect_float(value, field_name=field_name)


def expect_float(value: object, *, field_name: str) -> float:
    if not isinstance(value, int | float) or isinstance(value, bool):
        raise EvalDatasetError(f"{field_name} must be a number")
    return float(value)


def parse_required_str_tuple(value: object, *, field_name: str) -> tuple[str, ...]:
    values = parse_str_tuple(value, field_name=field_name)
    if not values:
        raise EvalDatasetError(f"{field_name} must not be empty")
    return values


def parse_str_tuple(value: object, *, field_name: str) -> tuple[str, ...]:
    items = expect_list(value, field_name=field_name)
    return tuple(
        expect_nonempty_str(item, field_name=f"{field_name}[{index}]")
        for index, item in enumerate(items)
    )


def parse_float_tuple(
    value: object,
    *,
    field_name: str,
) -> tuple[float, ...] | None:
    if value is None:
        return None
    items = expect_list(value, field_name=field_name)
    return tuple(
        expect_float(item, field_name=f"{field_name}[{index}]")
        for index, item in enumerate(items)
    )
