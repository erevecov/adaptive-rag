"""Five-field cron validation, DST behavior, and misfire policies."""

from datetime import UTC, datetime
from zoneinfo import ZoneInfo

import pytest

from adaptive_rag.jobs.scheduler import (
    apply_misfire_policy,
    schedule_occurrences,
    validate_cron_schedule,
)

MISSED = [datetime(2026, 8, 10, hour, 0, tzinfo=UTC) for hour in range(1, 5)]


def test_spring_forward_nonexistent_local_time_is_skipped() -> None:
    occurrences = schedule_occurrences(
        expression="30 2 * * *",
        timezone="America/New_York",
        after_utc=datetime(2026, 3, 7, tzinfo=UTC),
        through_utc=datetime(2026, 3, 9, 23, 59, tzinfo=UTC),
        limit=10,
    )

    assert [
        value.astimezone(ZoneInfo("America/New_York")).day for value in occurrences
    ] == [7, 9]


def test_fall_back_repeated_local_time_produces_two_utc_instants() -> None:
    occurrences = schedule_occurrences(
        expression="30 1 * * *",
        timezone="America/New_York",
        after_utc=datetime(2026, 10, 31, tzinfo=UTC),
        through_utc=datetime(2026, 11, 2, tzinfo=UTC),
        limit=10,
    )
    repeated = [
        value
        for value in occurrences
        if value.astimezone(ZoneInfo("America/New_York")).date().isoformat()
        == "2026-11-01"
    ]

    assert len(repeated) == 2
    assert repeated[0] != repeated[1]
    assert all(
        value.astimezone(ZoneInfo("America/New_York")).hour == 1 for value in repeated
    )


def test_run_once_returns_only_latest_missed_occurrence() -> None:
    assert apply_misfire_policy(MISSED, "run_once", max_catch_up=10) == [MISSED[-1]]


def test_skip_and_catch_up_misfire_policies_are_bounded() -> None:
    assert apply_misfire_policy(MISSED, "skip", max_catch_up=10) == []
    assert apply_misfire_policy(MISSED, "catch_up", max_catch_up=2) == MISSED[:2]


@pytest.mark.parametrize(
    "expression",
    ["* * * * * *", "@daily", "0 0 1 1 * 2027"],
)
def test_validation_rejects_non_five_field_or_alias_cron(expression: str) -> None:
    with pytest.raises(ValueError):
        validate_cron_schedule(
            expression=expression,
            timezone="UTC",
            max_catch_up=1,
        )


def test_validation_rejects_unknown_timezone_and_unbounded_catch_up() -> None:
    with pytest.raises(ValueError):
        validate_cron_schedule(
            expression="0 * * * *",
            timezone="Mars/Olympus_Mons",
            max_catch_up=1,
        )
    with pytest.raises(ValueError):
        validate_cron_schedule(
            expression="0 * * * *",
            timezone="UTC",
            max_catch_up=101,
        )
