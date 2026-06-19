from __future__ import annotations

import json

from typer.testing import CliRunner

from adaptive_rag.chat import ChatRunnerRequest
from adaptive_rag.chat.tools import ChatTools
from adaptive_rag.cli.app import app
from adaptive_rag.provider_usage import ProviderBudgetExceededError


def test_provider_embedding_smoke_outputs_json_for_fake_provider() -> None:
    result = CliRunner().invoke(
        app,
        [
            "providers",
            "embedding-smoke",
            "--text",
            "alpha",
        ],
    )

    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert data == {
        "provider": "fake",
        "model": "fake-embedding-v1",
        "dimensions": 1024,
        "input_count": 1,
        "embedding_count": 1,
    }


def test_provider_chat_smoke_outputs_json_for_fake_runner() -> None:
    result = CliRunner().invoke(
        app,
        [
            "providers",
            "chat-smoke",
            "--message",
            "What supports alpha?",
        ],
    )

    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert data == {
        "provider": "fake",
        "model": "retrieval-grounded-local-v1",
        "answer": "Alpha smoke evidence",
        "citation_count": 1,
        "tool_call_count": 1,
    }


def test_provider_embedding_smoke_reports_budget_errors(monkeypatch) -> None:
    class BudgetBlockedProvider:
        provider_name = "qwen"
        model_name = "text-embedding-v4"
        dimensions = 1024

        def embed_texts(self, _texts: list[str]) -> list[list[float]]:
            raise ProviderBudgetExceededError("provider budget exceeded")

    monkeypatch.setattr(
        "adaptive_rag.cli.providers.get_cli_dense_embedding_provider",
        lambda: BudgetBlockedProvider(),
    )

    result = CliRunner().invoke(app, ["providers", "embedding-smoke"])

    assert result.exit_code == 1
    assert "provider budget exceeded" in result.stderr


def test_provider_chat_smoke_reports_budget_errors(monkeypatch) -> None:
    class BudgetBlockedRunner:
        provider_name = "qwen"
        model_name = "qwen-plus"

        def run(
            self,
            _request: ChatRunnerRequest,
            _tools: ChatTools,
        ):
            raise ProviderBudgetExceededError("provider budget exceeded")

    monkeypatch.setattr(
        "adaptive_rag.cli.providers.get_cli_chat_runner",
        lambda: BudgetBlockedRunner(),
    )

    result = CliRunner().invoke(app, ["providers", "chat-smoke"])

    assert result.exit_code == 1
    assert "provider budget exceeded" in result.stderr
