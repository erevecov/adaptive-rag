from __future__ import annotations

import json

from typer.testing import CliRunner

from adaptive_rag.cli.app import app


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
