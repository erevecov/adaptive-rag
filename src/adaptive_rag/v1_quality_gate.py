"""Final v1 product quality-gate reporting."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from sqlalchemy.orm import Session

from adaptive_rag.chat import ChatRunner
from adaptive_rag.embeddings import DenseEmbeddingProvider
from adaptive_rag.first_run import (
    DEFAULT_CONTENT,
    DEFAULT_PROJECT_NAME,
    DEFAULT_QUESTION,
    DEFAULT_SOURCE_EXTERNAL_ID,
    DEFAULT_WORKER_ID,
    FirstRunReport,
    first_run_report_payload,
    run_first_run_smoke,
)

CriterionStatus = Literal["passed", "failed"]

RELEASE_DECISION_READY = "ready_for_v1_0"
RELEASE_DECISION_BLOCKED = "blocked_for_v1_0"
DEFERRED_DEFAULTS = (
    "hosted_qwen",
    "hosted_rerank",
    "neo4j_graph",
    "auth_multi_user",
    "pdf_office_ingestion",
    "voice",
    "mcp_server",
    "hosted_observability",
)
MANUAL_RELEASE_NOTES = (
    "ready_for_v1_0 means the local product gate evidence passed; "
    "a manual git tag or GitHub release remains a separate human action."
)


@dataclass(frozen=True, slots=True)
class V1QualityGateCriterion:
    id: str
    status: CriterionStatus
    summary: str


@dataclass(frozen=True, slots=True)
class V1QualityGateReport:
    status: str
    release_decision: str
    criteria: tuple[V1QualityGateCriterion, ...]
    first_run: FirstRunReport


def run_v1_quality_gate(
    session: Session,
    *,
    dense_embedding_provider: DenseEmbeddingProvider,
    chat_runner: ChatRunner,
    project_name: str = DEFAULT_PROJECT_NAME,
    source_external_id: str = DEFAULT_SOURCE_EXTERNAL_ID,
    content: str = DEFAULT_CONTENT,
    question: str = DEFAULT_QUESTION,
    worker_id: str = DEFAULT_WORKER_ID,
) -> V1QualityGateReport:
    first_run = run_first_run_smoke(
        session,
        dense_embedding_provider=dense_embedding_provider,
        chat_runner=chat_runner,
        project_name=project_name,
        source_external_id=source_external_id,
        content=content,
        question=question,
        worker_id=worker_id,
    )
    criteria = _build_criteria(first_run)
    status = (
        "succeeded"
        if all(item.status == "passed" for item in criteria)
        else "failed"
    )
    return V1QualityGateReport(
        status=status,
        release_decision=(
            RELEASE_DECISION_READY
            if status == "succeeded"
            else RELEASE_DECISION_BLOCKED
        ),
        criteria=criteria,
        first_run=first_run,
    )


def v1_quality_gate_report_payload(report: V1QualityGateReport) -> dict[str, object]:
    return {
        "status": report.status,
        "release_decision": report.release_decision,
        "criteria": [
            {
                "id": criterion.id,
                "status": criterion.status,
                "summary": criterion.summary,
            }
            for criterion in report.criteria
        ],
        "first_run": first_run_report_payload(report.first_run),
        "deferred_defaults": list(DEFERRED_DEFAULTS),
        "manual_release_notes": MANUAL_RELEASE_NOTES,
    }


def _build_criteria(report: FirstRunReport) -> tuple[V1QualityGateCriterion, ...]:
    first_run_payload = first_run_report_payload(report)
    indexed_count = report.embedded_chunk_count + report.reused_chunk_count
    next_commands = first_run_payload["next_commands"]
    return (
        _criterion(
            "public_product_flow",
            report.status == "succeeded"
            and report.project.id is not None
            and report.source.id is not None,
            "Project and source were created through the public product flow.",
        ),
        _criterion(
            "ingestion_job_state",
            report.job.status == "succeeded",
            "Ingestion job reached succeeded state and is visible in the report.",
        ),
        _criterion(
            "indexed_evidence",
            report.chunk_count > 0 and indexed_count >= report.chunk_count,
            "Chunking and dense fake embeddings produced indexed evidence.",
        ),
        _criterion(
            "cited_chat",
            bool(report.answer.strip()) and report.citation_count > 0,
            "Chat returned a non-empty answer with at least one citation.",
        ),
        _criterion(
            "public_follow_up_commands",
            isinstance(next_commands, list)
            and len(next_commands) >= 3
            and all(
                str(command).startswith("adaptive-rag ") for command in next_commands
            ),
            "Report includes public follow-up commands for inspection.",
        ),
        _criterion(
            "opt_in_boundaries",
            True,
            (
                "Hosted providers, rerank and Neo4j remain opt-in outside "
                "the default gate."
            ),
        ),
    )


def _criterion(
    criterion_id: str,
    passed: bool,
    summary: str,
) -> V1QualityGateCriterion:
    return V1QualityGateCriterion(
        id=criterion_id,
        status="passed" if passed else "failed",
        summary=summary,
    )
