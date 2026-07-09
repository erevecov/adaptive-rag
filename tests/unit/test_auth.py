"""Tests de helpers de autenticación local."""

from __future__ import annotations

import logging

import pytest
from sqlalchemy.exc import OperationalError

from adaptive_rag import auth


class _RaisingScalarSession:
    """Session doble que falla el conteo con un OperationalError."""

    def __init__(self) -> None:
        self.rolled_back = False

    def scalar(self, statement: object) -> int:
        raise OperationalError("SELECT count(*)", {}, Exception("connection reset"))

    def rollback(self) -> None:
        self.rolled_back = True


def test_users_exist_logs_before_bootstrap_fallback(
    caplog: pytest.LogCaptureFixture,
) -> None:
    session = _RaisingScalarSession()

    with caplog.at_level(logging.WARNING, logger=auth.__name__):
        result = auth.users_exist(session)  # type: ignore[arg-type]

    assert result is False
    assert session.rolled_back is True
    records = [
        record
        for record in caplog.records
        if record.name == auth.__name__
        and "users_exist_check_failed" in record.getMessage()
    ]
    assert len(records) == 1
    assert records[0].levelno == logging.WARNING
    assert records[0].exc_info is not None
    assert records[0].exc_info[0] is OperationalError
