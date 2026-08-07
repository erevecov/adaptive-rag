"""Fallback model switch after primary 429/5xx."""

from __future__ import annotations

from uuid import uuid4

import pytest

from adaptive_rag.chat.models import ChatRunnerRequest
from adaptive_rag.chat.qwen import (
    QwenChatRunner,
    QwenChatRunnerError,
    _should_use_fallback,
)
from adaptive_rag.chat.tools import ChatRetrievalTool, ChatTools


class _SequenceClient:
    def __init__(self, outcomes: list[object]) -> None:
        self.outcomes = list(outcomes)
        self.models: list[str] = []

    def create_chat_completion(
        self,
        *,
        model: str,
        messages,  # noqa: ANN001
        tools=None,  # noqa: ANN001
        on_answer_delta=None,  # noqa: ANN001
    ):
        self.models.append(model)
        if not self.outcomes:
            raise AssertionError("unexpected extra call")
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    def request_cancel(self) -> None:
        return None


def _tools() -> ChatTools:
    return ChatTools(
        retrieval=ChatRetrievalTool(
            retrieval_service=object(),  # type: ignore[arg-type]
            project_id=uuid4(),
            default_limit=3,
            default_metadata_filter=None,
        )
    )


def _request() -> ChatRunnerRequest:
    return ChatRunnerRequest(
        project_id=uuid4(),
        message="hello",
        retrieval_limit=3,
        metadata_filter=None,
    )


def _completion(content: str) -> dict:
    return {
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": content,
                }
            }
        ]
    }


def test_should_use_fallback_guards() -> None:
    err = QwenChatRunnerError("qwen chat request failed with status 429")
    assert _should_use_fallback(err, "qwen-plus", "qwen3.7-plus") is True
    assert _should_use_fallback(err, None, "qwen3.7-plus") is False
    assert _should_use_fallback(err, "qwen3.7-plus", "qwen3.7-plus") is False
    assert (
        _should_use_fallback(
            QwenChatRunnerError("bad request 400"),
            "qwen-plus",
            "qwen3.7-plus",
        )
        is False
    )


def test_runner_switches_to_fallback_model_after_429() -> None:
    client = _SequenceClient(
        [
            QwenChatRunnerError("qwen chat request failed with status 429"),
            _completion('{"answer":"from fallback","cited_chunk_ids":[]}'),
        ]
    )
    runner = QwenChatRunner(
        model_name="primary-model",
        client=client,  # type: ignore[arg-type]
        fallback_model_name="secondary-model",
    )

    output = runner.run(_request(), _tools())

    assert output.answer == "from fallback"
    assert runner.used_fallback is True
    assert runner.last_used_model == "secondary-model"
    assert client.models == ["primary-model", "secondary-model"]


def test_runner_does_not_fallback_without_configured_model() -> None:
    client = _SequenceClient(
        [QwenChatRunnerError("qwen chat request failed with status 429")]
    )
    runner = QwenChatRunner(
        model_name="primary-model",
        client=client,  # type: ignore[arg-type]
        fallback_model_name=None,
    )

    with pytest.raises(QwenChatRunnerError, match="429"):
        runner.run(_request(), _tools())

    assert runner.used_fallback is False
    assert client.models == ["primary-model"]
