"""Accounting minimo de usage/costo para llamadas live a providers."""

from __future__ import annotations

import logging
from dataclasses import dataclass, replace
from decimal import Decimal
from typing import Literal, Protocol

ProviderOperation = Literal[
    "chat",
    "contextualize",
    "embedding",
    "rerank",
    "eval_judge",
]
ProviderCallOutcome = Literal["succeeded", "failed", "blocked"]
ProviderUsageSource = Literal["provider_reported", "estimated", "unavailable"]

logger = logging.getLogger(__name__)


class ProviderBudgetExceededError(ValueError):
    """Error estable cuando una llamada excede el presupuesto configurado."""


@dataclass(frozen=True, slots=True)
class ProviderTokenUsage:
    """Usage normalizado reportado o estimado por una llamada de provider."""

    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None
    input_count: int | None = None

    def has_tokens(self) -> bool:
        return any(
            value is not None
            for value in (
                self.input_tokens,
                self.output_tokens,
                self.total_tokens,
            )
        )


@dataclass(frozen=True, slots=True)
class ProviderPriceCatalog:
    """Snapshot configurable de precios usados para estimar costo."""

    chat_input_price_per_million_tokens_usd: float | None = None
    chat_output_price_per_million_tokens_usd: float | None = None
    embedding_input_price_per_million_tokens_usd: float | None = None
    rerank_input_price_per_million_tokens_usd: float | None = None


@dataclass(frozen=True, slots=True)
class ProviderCallRecord:
    """Registro estructurado de una llamada a provider, sin secretos."""

    provider: str
    model: str
    operation: ProviderOperation
    outcome: ProviderCallOutcome
    duration_ms: int
    usage: ProviderTokenUsage
    usage_source: ProviderUsageSource
    estimated_cost_usd: float | None = None
    request_id: str | None = None
    error_type: str | None = None

    def as_log_extra(self) -> dict[str, object]:
        return {
            "provider": self.provider,
            "model": self.model,
            "operation": self.operation,
            "outcome": self.outcome,
            "duration_ms": self.duration_ms,
            "input_tokens": self.usage.input_tokens,
            "output_tokens": self.usage.output_tokens,
            "total_tokens": self.usage.total_tokens,
            "input_count": self.usage.input_count,
            "usage_source": self.usage_source,
            "estimated_cost_usd": self.estimated_cost_usd,
            "request_id": self.request_id,
            "error_type": self.error_type,
        }


class ProviderUsageTracker(Protocol):
    """Sink para registros de llamadas live."""

    def record(self, record: ProviderCallRecord) -> None:
        """Registra metadata estructurada de una llamada a provider."""


@dataclass(slots=True)
class InMemoryProviderUsageTracker:
    """Tracker simple para tests, smokes y wiring inicial."""

    _records: list[ProviderCallRecord] | None = None

    @property
    def records(self) -> tuple[ProviderCallRecord, ...]:
        return tuple(self._active_records)

    def record(self, record: ProviderCallRecord) -> None:
        self._active_records.append(record)
        logger.info("provider_call", extra={"provider_call": record.as_log_extra()})

    @property
    def _active_records(self) -> list[ProviderCallRecord]:
        if self._records is None:
            self._records = []
        return self._records


@dataclass(frozen=True, slots=True)
class ProviderBudgetGuard:
    """Valida presupuesto por request/corrida."""

    max_cost_usd: float | None = None

    def enforce(self, record: ProviderCallRecord) -> None:
        if self.max_cost_usd is None or record.estimated_cost_usd is None:
            return
        if record.estimated_cost_usd <= self.max_cost_usd:
            return
        raise ProviderBudgetExceededError(
            "provider budget exceeded: "
            f"estimated {record.estimated_cost_usd:g} USD exceeds "
            f"limit {self.max_cost_usd:g} USD"
        )


def estimate_cost_usd(
    *,
    operation: ProviderOperation,
    usage: ProviderTokenUsage,
    price_catalog: ProviderPriceCatalog,
) -> float | None:
    if operation == "chat":
        return _chat_cost_usd(usage=usage, price_catalog=price_catalog)
    if operation == "embedding":
        return _embedding_cost_usd(usage=usage, price_catalog=price_catalog)
    if operation == "rerank":
        return _rerank_cost_usd(usage=usage, price_catalog=price_catalog)
    return None


def extract_usage(
    response_data: object,
    *,
    operation: ProviderOperation,
    input_count: int | None = None,
) -> tuple[ProviderTokenUsage, ProviderUsageSource]:
    if not isinstance(response_data, dict):
        return (
            ProviderTokenUsage(input_count=input_count),
            "unavailable",
        )

    usage_data = response_data.get("usage")
    if not isinstance(usage_data, dict):
        return (
            ProviderTokenUsage(input_count=input_count),
            "unavailable",
        )

    prompt_tokens = _optional_int(
        usage_data.get("prompt_tokens", usage_data.get("input_tokens"))
    )
    completion_tokens = _optional_int(
        usage_data.get("completion_tokens", usage_data.get("output_tokens"))
    )
    total_tokens = _optional_int(usage_data.get("total_tokens"))
    if operation in ("embedding", "rerank") and prompt_tokens is None:
        prompt_tokens = total_tokens

    usage = ProviderTokenUsage(
        input_tokens=prompt_tokens,
        output_tokens=completion_tokens,
        total_tokens=total_tokens,
        input_count=input_count,
    )
    return usage, "provider_reported" if usage.has_tokens() else "unavailable"


def build_success_record(
    *,
    provider: str,
    model: str,
    operation: ProviderOperation,
    duration_ms: int,
    response_data: object,
    price_catalog: ProviderPriceCatalog,
    request_id: str | None = None,
    input_count: int | None = None,
) -> ProviderCallRecord:
    usage, usage_source = extract_usage(
        response_data,
        operation=operation,
        input_count=input_count,
    )
    return ProviderCallRecord(
        provider=provider,
        model=model,
        operation=operation,
        outcome="succeeded",
        duration_ms=duration_ms,
        usage=usage,
        usage_source=usage_source,
        estimated_cost_usd=estimate_cost_usd(
            operation=operation,
            usage=usage,
            price_catalog=price_catalog,
        ),
        request_id=request_id,
    )


def build_failure_record(
    *,
    provider: str,
    model: str,
    operation: ProviderOperation,
    duration_ms: int,
    error: Exception,
    input_count: int | None = None,
) -> ProviderCallRecord:
    return ProviderCallRecord(
        provider=provider,
        model=model,
        operation=operation,
        outcome="failed",
        duration_ms=duration_ms,
        usage=ProviderTokenUsage(input_count=input_count),
        usage_source="unavailable",
        error_type=type(error).__name__,
    )


def record_with_budget(
    *,
    record: ProviderCallRecord,
    tracker: ProviderUsageTracker | None,
    budget_guard: ProviderBudgetGuard | None,
) -> None:
    try:
        if budget_guard is not None:
            budget_guard.enforce(record)
    except ProviderBudgetExceededError:
        blocked = replace(record, outcome="blocked")
        if tracker is not None:
            tracker.record(blocked)
        raise

    if tracker is not None:
        tracker.record(record)


def _chat_cost_usd(
    *,
    usage: ProviderTokenUsage,
    price_catalog: ProviderPriceCatalog,
) -> float | None:
    input_cost = _token_cost(
        token_count=usage.input_tokens,
        price_per_million=price_catalog.chat_input_price_per_million_tokens_usd,
    )
    output_cost = _token_cost(
        token_count=usage.output_tokens,
        price_per_million=price_catalog.chat_output_price_per_million_tokens_usd,
    )
    return _sum_costs(input_cost, output_cost)


def _embedding_cost_usd(
    *,
    usage: ProviderTokenUsage,
    price_catalog: ProviderPriceCatalog,
) -> float | None:
    return _sum_costs(
        _token_cost(
            token_count=usage.input_tokens,
            price_per_million=(
                price_catalog.embedding_input_price_per_million_tokens_usd
            ),
        ),
    )


def _rerank_cost_usd(
    *,
    usage: ProviderTokenUsage,
    price_catalog: ProviderPriceCatalog,
) -> float | None:
    return _sum_costs(
        _token_cost(
            token_count=usage.input_tokens,
            price_per_million=price_catalog.rerank_input_price_per_million_tokens_usd,
        ),
    )


def _token_cost(
    *,
    token_count: int | None,
    price_per_million: float | None,
) -> Decimal | None:
    if token_count is None or price_per_million is None:
        return None
    return (Decimal(token_count) * Decimal(str(price_per_million))) / Decimal(
        1_000_000
    )


def _sum_costs(*costs: Decimal | None) -> float | None:
    active = [cost for cost in costs if cost is not None]
    if not active:
        return None
    total: Decimal = sum(active, Decimal("0"))
    return float(round(total, 12))


def _optional_int(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return None
