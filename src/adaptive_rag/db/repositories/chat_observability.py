"""Read models for chat observability summaries."""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from math import ceil
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from adaptive_rag.db.models import (
    CHAT_SESSION_STATUS_VALUES,
    ChatSession,
    ProviderUsage,
)

MAX_ERROR_MESSAGE_LENGTH = 160
MAX_TOP_ERROR_MESSAGES = 10


@dataclass(frozen=True)
class ChatObservabilityFilters:
    """Filters applied to a chat observability summary."""

    created_at_from: datetime | None = None
    created_at_to: datetime | None = None
    status: str | None = None


@dataclass(frozen=True)
class ChatObservabilityLatencySummary:
    """Portable latency aggregate over known millisecond values."""

    count: int
    min: int | None
    avg: float | None
    p50: int | None
    p95: int | None
    max: int | None


@dataclass(frozen=True)
class ChatObservabilitySessionSummary:
    """Session volume and status aggregate."""

    total: int
    by_status: dict[str, int]


@dataclass(frozen=True)
class ChatObservabilityProviderUsageGroup:
    """Provider usage aggregate for one operation/provider/model key."""

    operation: str
    provider: str
    model: str
    record_count: int
    estimated_cost_usd: float | None
    input_tokens: int | None
    output_tokens: int | None
    total_tokens: int | None
    input_count: int | None
    latency_ms: ChatObservabilityLatencySummary


@dataclass(frozen=True)
class ChatObservabilityProviderUsageSummary:
    """Provider usage aggregate for the filtered project."""

    total_records: int
    total_estimated_cost_usd: float
    missing_cost_count: int
    groups: tuple[ChatObservabilityProviderUsageGroup, ...]


@dataclass(frozen=True)
class ChatObservabilityErrorMessage:
    """Safe aggregated error message."""

    message: str
    count: int


@dataclass(frozen=True)
class ChatObservabilityErrorSummary:
    """Error counts and safe top messages."""

    session_error_count: int
    provider_error_count: int
    top_messages: tuple[ChatObservabilityErrorMessage, ...]


@dataclass(frozen=True)
class ChatObservabilitySummary:
    """Read-only chat observability summary for one project."""

    project_id: UUID
    filters: ChatObservabilityFilters
    sessions: ChatObservabilitySessionSummary
    provider_usage: ChatObservabilityProviderUsageSummary
    errors: ChatObservabilityErrorSummary


class ChatObservabilityRepository:
    """Read-only observability aggregates over existing chat audit tables."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get_summary(
        self,
        *,
        project_id: UUID,
        created_at_from: datetime | None = None,
        created_at_to: datetime | None = None,
        status: str | None = None,
    ) -> ChatObservabilitySummary:
        _validate_filters(
            created_at_from=created_at_from,
            created_at_to=created_at_to,
            status=status,
        )
        filters = ChatObservabilityFilters(
            created_at_from=created_at_from,
            created_at_to=created_at_to,
            status=status,
        )
        sessions = self._list_sessions(
            project_id=project_id,
            created_at_from=created_at_from,
            created_at_to=created_at_to,
            status=status,
        )
        provider_usage = self._list_provider_usage(
            project_id=project_id,
            created_at_from=created_at_from,
            created_at_to=created_at_to,
            status=status,
        )
        return ChatObservabilitySummary(
            project_id=project_id,
            filters=filters,
            sessions=_summarize_sessions(sessions),
            provider_usage=_summarize_provider_usage(provider_usage),
            errors=_summarize_errors(
                session_errors=[
                    chat_session.error_message for chat_session in sessions
                ],
                provider_errors=[usage.error_message for usage in provider_usage],
            ),
        )

    def _list_sessions(
        self,
        *,
        project_id: UUID,
        created_at_from: datetime | None,
        created_at_to: datetime | None,
        status: str | None,
    ) -> tuple[ChatSession, ...]:
        statement = select(ChatSession).where(ChatSession.project_id == project_id)
        if created_at_from is not None:
            statement = statement.where(ChatSession.created_at >= created_at_from)
        if created_at_to is not None:
            statement = statement.where(ChatSession.created_at < created_at_to)
        if status is not None:
            statement = statement.where(ChatSession.status == status)
        statement = statement.order_by(ChatSession.created_at, ChatSession.id)
        return tuple(self._session.scalars(statement).all())

    def _list_provider_usage(
        self,
        *,
        project_id: UUID,
        created_at_from: datetime | None,
        created_at_to: datetime | None,
        status: str | None,
    ) -> tuple[ProviderUsage, ...]:
        statement = select(ProviderUsage).where(ProviderUsage.project_id == project_id)
        if status is not None:
            statement = statement.join(
                ChatSession,
                ProviderUsage.session_id == ChatSession.id,
            ).where(
                ChatSession.project_id == project_id,
                ChatSession.status == status,
            )
        if created_at_from is not None:
            statement = statement.where(ProviderUsage.created_at >= created_at_from)
        if created_at_to is not None:
            statement = statement.where(ProviderUsage.created_at < created_at_to)
        statement = statement.order_by(
            ProviderUsage.operation,
            ProviderUsage.provider,
            ProviderUsage.model,
            ProviderUsage.created_at,
            ProviderUsage.id,
        )
        return tuple(self._session.scalars(statement).all())


def _validate_filters(
    *,
    created_at_from: datetime | None,
    created_at_to: datetime | None,
    status: str | None,
) -> None:
    if status is not None and status not in CHAT_SESSION_STATUS_VALUES:
        raise ValueError("invalid chat session status")
    if (
        created_at_from is not None
        and created_at_to is not None
        and created_at_from >= created_at_to
    ):
        raise ValueError("created_at_from must be before created_at_to")


def _summarize_sessions(
    sessions: tuple[ChatSession, ...],
) -> ChatObservabilitySessionSummary:
    by_status = {status: 0 for status in CHAT_SESSION_STATUS_VALUES}
    for chat_session in sessions:
        by_status[chat_session.status] = by_status.get(chat_session.status, 0) + 1
    return ChatObservabilitySessionSummary(
        total=len(sessions),
        by_status=by_status,
    )


def _summarize_provider_usage(
    usages: tuple[ProviderUsage, ...],
) -> ChatObservabilityProviderUsageSummary:
    groups_by_key: dict[tuple[str, str, str], list[ProviderUsage]] = {}
    for usage in usages:
        key = (usage.operation, usage.provider, usage.model)
        groups_by_key.setdefault(key, []).append(usage)

    groups = tuple(
        _summarize_provider_usage_group(key=key, usages=tuple(group_usages))
        for key, group_usages in sorted(groups_by_key.items(), key=lambda item: item[0])
    )
    known_costs = [
        usage.estimated_cost_usd
        for usage in usages
        if usage.estimated_cost_usd is not None
    ]
    return ChatObservabilityProviderUsageSummary(
        total_records=len(usages),
        total_estimated_cost_usd=sum(known_costs),
        missing_cost_count=sum(
            1 for usage in usages if usage.estimated_cost_usd is None
        ),
        groups=groups,
    )


def _summarize_provider_usage_group(
    *,
    key: tuple[str, str, str],
    usages: tuple[ProviderUsage, ...],
) -> ChatObservabilityProviderUsageGroup:
    operation, provider, model = key
    known_costs = [
        usage.estimated_cost_usd
        for usage in usages
        if usage.estimated_cost_usd is not None
    ]
    return ChatObservabilityProviderUsageGroup(
        operation=operation,
        provider=provider,
        model=model,
        record_count=len(usages),
        estimated_cost_usd=sum(known_costs) if known_costs else None,
        input_tokens=_sum_known(usage.input_tokens for usage in usages),
        output_tokens=_sum_known(usage.output_tokens for usage in usages),
        total_tokens=_sum_known(usage.total_tokens for usage in usages),
        input_count=_sum_known(usage.input_count for usage in usages),
        latency_ms=_summarize_latencies(usage.latency_ms for usage in usages),
    )


def _sum_known(values: Iterable[int | None]) -> int | None:
    known_values = [value for value in values if value is not None]
    if not known_values:
        return None
    return sum(known_values)


def _summarize_latencies(
    values: Iterable[int | None],
) -> ChatObservabilityLatencySummary:
    known_values = sorted(value for value in values if value is not None)
    if not known_values:
        return ChatObservabilityLatencySummary(
            count=0,
            min=None,
            avg=None,
            p50=None,
            p95=None,
            max=None,
        )
    return ChatObservabilityLatencySummary(
        count=len(known_values),
        min=known_values[0],
        avg=sum(known_values) / len(known_values),
        p50=_nearest_rank_percentile(known_values, 50),
        p95=_nearest_rank_percentile(known_values, 95),
        max=known_values[-1],
    )


def _nearest_rank_percentile(values: list[int], percentile: int) -> int:
    index = ceil((percentile / 100) * len(values)) - 1
    bounded_index = max(0, min(index, len(values) - 1))
    return values[bounded_index]


def _summarize_errors(
    *,
    session_errors: list[str | None],
    provider_errors: list[str | None],
) -> ChatObservabilityErrorSummary:
    counter: Counter[str] = Counter()
    session_error_count = _count_errors(session_errors, counter=counter)
    provider_error_count = _count_errors(provider_errors, counter=counter)
    top_messages = tuple(
        ChatObservabilityErrorMessage(message=message, count=count)
        for message, count in sorted(
            counter.items(),
            key=lambda item: (-item[1], item[0]),
        )[:MAX_TOP_ERROR_MESSAGES]
    )
    return ChatObservabilityErrorSummary(
        session_error_count=session_error_count,
        provider_error_count=provider_error_count,
        top_messages=top_messages,
    )


def _count_errors(
    errors: list[str | None],
    *,
    counter: Counter[str],
) -> int:
    count = 0
    for error in errors:
        message = _safe_error_message(error)
        if message is None:
            continue
        count += 1
        counter[message] += 1
    return count


def _safe_error_message(error: str | None) -> str | None:
    if error is None:
        return None
    message = error.strip()
    if not message:
        return None
    return message[:MAX_ERROR_MESSAGE_LENGTH]
