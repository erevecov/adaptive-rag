"""Tests del runner agregado de evals M6."""

from __future__ import annotations

import json
from pathlib import Path

from sqlalchemy.orm import Session

from adaptive_rag.db.base import Base
from adaptive_rag.db.models import (
    EMBEDDING_DIMENSIONS,
    Chunk,
    Document,
    DocumentVersion,
    Project,
    Source,
)
from adaptive_rag.db.session import create_engine_from_url, create_session_factory
from adaptive_rag.evals import load_eval_suite, run_eval_suite


class MappingEmbeddingProvider:
    provider_name = "fake"
    model_name = "eval-mapping-v1"
    dimensions = EMBEDDING_DIMENSIONS

    def __init__(self, mapping: dict[str, list[float]]) -> None:
        self._mapping = mapping

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [list(self._mapping[text]) for text in texts]


def test_run_eval_suite_combines_retrieval_and_chat_reports(tmp_path: Path) -> None:
    suite = load_eval_suite(
        _write_suite(
            tmp_path,
            {
                "schema_version": 1,
                "suite_id": "combined-smoke",
                "thresholds": {
                    "retrieval_hit_rate": 1.0,
                    "chat_citation_coverage": 1.0,
                },
                "evidence": [
                    {
                        "id": "alpha",
                        "text": "Alpha original evidence",
                        "source_type": "markdown",
                        "source_external_id": "alpha.md",
                    },
                    {
                        "id": "far",
                        "text": "Far unrelated evidence",
                        "source_type": "markdown",
                        "source_external_id": "far.md",
                    },
                ],
                "retrieval_cases": [
                    {
                        "id": "retrieve-alpha",
                        "query": "Alpha original evidence",
                        "limit": 2,
                        "expected_evidence_ids": ["alpha"],
                    }
                ],
                "chat_cases": [
                    {
                        "id": "chat-alpha",
                        "message": "Alpha original evidence",
                        "retrieval_limit": 2,
                        "expected_evidence_ids": ["alpha"],
                        "expected_tool_queries": ["Alpha original evidence"],
                    }
                ],
            },
        )
    )
    provider = MappingEmbeddingProvider(
        {
            "Alpha original evidence": _vector(0.0),
            "Far unrelated evidence": _vector(0.9),
        }
    )

    report = run_eval_suite(_make_session(), suite, provider=provider)

    assert report.status == "passed"
    assert report.metrics == {
        "chat_case_count": 1.0,
        "chat_citation_coverage": 1.0,
        "chat_passed_count": 1.0,
        "retrieval_case_count": 1.0,
        "retrieval_hit_rate": 1.0,
        "retrieval_passed_count": 1.0,
    }
    assert report.thresholds == {
        "chat_citation_coverage": 1.0,
        "retrieval_hit_rate": 1.0,
    }
    assert [case.id for case in report.cases] == ["retrieve-alpha", "chat-alpha"]


def _make_session() -> Session:
    engine = create_engine_from_url("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(
        engine,
        tables=[
            Project.__table__,
            Source.__table__,
            Document.__table__,
            DocumentVersion.__table__,
            Chunk.__table__,
        ],
    )
    return create_session_factory(engine)()


def _write_suite(tmp_path: Path, payload: object) -> Path:
    suite_path = tmp_path / "suite.json"
    suite_path.write_text(json.dumps(payload), encoding="utf-8")
    return suite_path


def _vector(first: float) -> list[float]:
    values = [0.0] * EMBEDDING_DIMENSIONS
    values[0] = first
    return values
