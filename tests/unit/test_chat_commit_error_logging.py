"""Tests de propagación de errores en el commit de auditoría de chat."""

from __future__ import annotations

import logging

import pytest

from adaptive_rag.api.routes import chat as api_chat
from adaptive_rag.cli import chat as cli_chat


class _FailingCommitSession:
    """Session doble cuyo commit falla y registra el rollback."""

    def __init__(self) -> None:
        self.rolled_back = False

    def commit(self) -> None:
        raise RuntimeError("commit failed")

    def rollback(self) -> None:
        self.rolled_back = True


@pytest.mark.parametrize(
    ("module", "logger_name"),
    [
        (api_chat, "adaptive_rag.api.routes.chat"),
        (cli_chat, "adaptive_rag.cli.chat"),
    ],
)
def test_commit_or_rollback_logs_commit_failure(
    module: object,
    logger_name: str,
    caplog: pytest.LogCaptureFixture,
) -> None:
    session = _FailingCommitSession()

    with caplog.at_level(logging.WARNING, logger=logger_name):
        module._commit_or_rollback_chat_error(session)  # type: ignore[attr-defined]

    assert session.rolled_back is True
    records = [
        record
        for record in caplog.records
        if record.name == logger_name
        and "chat_error_audit_commit_failed" in record.getMessage()
    ]
    assert len(records) == 1
    assert records[0].levelno == logging.WARNING
    assert records[0].exc_info is not None
    assert records[0].exc_info[0] is RuntimeError
