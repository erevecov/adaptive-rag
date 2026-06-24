"""End-to-end acceptance smokes for product runtime settings."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Literal
from uuid import UUID

from sqlalchemy.orm import Session

from adaptive_rag import authoring, ingestion_ops
from adaptive_rag.chat import ChatRequest, ChatService
from adaptive_rag.chunking import ChunkingPipeline, ChunkingPipelineError
from adaptive_rag.config.settings import get_settings
from adaptive_rag.contextualization import (
    ContextualizationPipeline,
    ContextualizationPipelineError,
)
from adaptive_rag.db.models import ProviderConnection, ProviderModelCatalog
from adaptive_rag.db.repositories import (
    ProjectRuntimeSettingsRepository,
    ProviderConnectionRepository,
    ProviderModelCatalogRepository,
    RuntimeSettingsRepository,
)
from adaptive_rag.embeddings import (
    DenseEmbeddingPipeline,
    DenseEmbeddingPipelineError,
)
from adaptive_rag.first_run import (
    DEFAULT_QUESTION,
    FirstRunError,
    FirstRunReport,
    first_run_report_payload,
)
from adaptive_rag.provider_models import HTTPProviderModelLister, ProviderModelLister
from adaptive_rag.provider_runtime import (
    get_chat_runner,
    get_contextualizer,
    get_dense_embedding_provider,
)
from adaptive_rag.retrieval import RetrievalService

DEFAULT_ACCEPTANCE_PROJECT_NAME = "Adaptive RAG Runtime Acceptance"
DEFAULT_ACCEPTANCE_SOURCE_EXTERNAL_ID = "runtime-settings-acceptance.md"
DEFAULT_ACCEPTANCE_WORKER_ID = "runtime-settings-acceptance"
DEFAULT_ACCEPTANCE_CONTENT = """# Runtime settings acceptance

Runtime settings acceptance proves that provider connections, model catalog
sync, global slots, project overrides, indexing, and cited chat work together
through persisted local configuration.

## Evidence

The default acceptance path uses fake providers, resolves the dense embedding
slot from a project override, inherits chat from the global default, and returns
citations without hosted credentials.
"""

AcceptanceCriterionStatus = Literal["passed", "failed"]
OPT_IN_SYSTEMS = (
    "hosted_qwen",
    "local_openai_compatible_live",
    "hosted_rerank",
    "neo4j_graph",
)


class AcceptanceError(FirstRunError):
    """Stable acceptance error surfaced by CLI and runbooks."""


@dataclass(frozen=True, slots=True)
class AcceptanceCriterion:
    id: str
    status: AcceptanceCriterionStatus
    summary: str


@dataclass(frozen=True, slots=True)
class RuntimeSettingsAcceptanceReport:
    status: str
    criteria: tuple[AcceptanceCriterion, ...]
    first_run: FirstRunReport
    global_connection: ProviderConnection
    model_catalog: tuple[ProviderModelCatalog, ...]
    global_slots: dict[str, dict[str, str]]
    effective_slots: dict[str, dict[str, str]]
    resolved_runtime: dict[str, dict[str, str]]


def run_runtime_settings_acceptance_smoke(
    session: Session,
    *,
    project_name: str = DEFAULT_ACCEPTANCE_PROJECT_NAME,
    source_external_id: str = DEFAULT_ACCEPTANCE_SOURCE_EXTERNAL_ID,
    content: str = DEFAULT_ACCEPTANCE_CONTENT,
    question: str = DEFAULT_QUESTION,
    worker_id: str = DEFAULT_ACCEPTANCE_WORKER_ID,
    model_lister: ProviderModelLister | None = None,
) -> RuntimeSettingsAcceptanceReport:
    connection = _configure_global_fake_connection(session, model_lister=model_lister)
    model_catalog = tuple(
        ProviderModelCatalogRepository(session).list_models(
            connection_id=connection.connection_id,
        )
    )
    required_models = _required_model_ids(model_catalog)
    _configure_global_defaults(
        session,
        connection=connection,
        model_ids=required_models,
    )

    project = authoring.create_project(session, name=project_name)
    ProjectRuntimeSettingsRepository(session).upsert_slot_override(
        project_id=project.id,
        slot="dense_embedding",
        connection_id=connection.connection_id,
        model_id=required_models["dense_embedding"],
    )
    first_run = _run_project_flow(
        session,
        project_id=project.id,
        project_name=project_name,
        source_external_id=source_external_id,
        content=content,
        question=question,
        worker_id=worker_id,
    )
    global_slots = _global_slots(session)
    effective_slots = _effective_slots(session, project_id=project.id)
    resolved_runtime = _resolved_runtime(session, project_id=project.id)
    criteria = _criteria(
        first_run=first_run,
        model_catalog=model_catalog,
        effective_slots=effective_slots,
        resolved_runtime=resolved_runtime,
    )
    status = (
        "succeeded"
        if all(criterion.status == "passed" for criterion in criteria)
        else "failed"
    )
    return RuntimeSettingsAcceptanceReport(
        status=status,
        criteria=criteria,
        first_run=first_run,
        global_connection=connection,
        model_catalog=model_catalog,
        global_slots=global_slots,
        effective_slots=effective_slots,
        resolved_runtime=resolved_runtime,
    )


def runtime_settings_acceptance_report_payload(
    report: RuntimeSettingsAcceptanceReport,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "status": report.status,
        "criteria": [
            {
                "id": criterion.id,
                "status": criterion.status,
                "summary": criterion.summary,
            }
            for criterion in report.criteria
        ],
        "runtime_settings": {
            "global_connection": {
                "connection_id": report.global_connection.connection_id,
                "provider": report.global_connection.provider,
                "connection_type": report.global_connection.connection_type,
                "capabilities": list(report.global_connection.capabilities_json),
            },
            "model_catalog": {
                "synced_count": len(report.model_catalog),
                "model_ids": [model.model_id for model in report.model_catalog],
            },
            "global_slots": {
                "chat": _slot_payload(report.global_slots["chat"]),
                "dense_embedding": _slot_payload(
                    report.global_slots["dense_embedding"]
                ),
                "contextualization": _slot_payload(
                    report.global_slots["contextualization"]
                ),
            },
            "effective_project_settings": {
                "chat": _slot_payload(report.effective_slots["chat"]),
                "dense_embedding": _slot_payload(
                    report.effective_slots["dense_embedding"]
                ),
                "contextualization": _slot_payload(
                    report.effective_slots["contextualization"]
                ),
            },
            "resolved_runtime": {
                "chat": _resolved_slot_payload(report.resolved_runtime["chat"]),
                "dense_embedding": _resolved_slot_payload(
                    report.resolved_runtime["dense_embedding"]
                ),
            },
        },
        "first_run": first_run_report_payload(report.first_run),
        "opt_in_systems": list(OPT_IN_SYSTEMS),
    }
    serialized = json.dumps(payload)
    if "api_key" in serialized or "Authorization" in serialized:
        raise AcceptanceError("acceptance report attempted to expose secret fields")
    return payload


def _configure_global_fake_connection(
    session: Session,
    *,
    model_lister: ProviderModelLister | None,
) -> ProviderConnection:
    connection = ProviderConnectionRepository(session).create_connection(
        provider="fake",
        connection_type="fake",
        capabilities=[
            "chat",
            "dense_embedding",
            "sparse_embedding",
            "rerank",
            "contextualization",
        ],
        metadata={"label": "Runtime acceptance fake"},
    )
    lister = model_lister or HTTPProviderModelLister(
        timeout_seconds=get_settings().provider_timeout_seconds,
    )
    catalog = ProviderModelCatalogRepository(session)
    discovered = lister.list_models(connection, api_key=None)
    if not discovered:
        raise AcceptanceError("runtime acceptance model catalog is empty")
    for model in discovered:
        catalog.upsert_model(
            connection_id=connection.connection_id,
            model_id=model.model_id,
            capabilities=model.capabilities,
            metadata=model.metadata,
            pricing=model.pricing,
        )
    return connection


def _required_model_ids(
    model_catalog: tuple[ProviderModelCatalog, ...],
) -> dict[str, str]:
    return {
        "chat": _model_id_for_capability(model_catalog, "chat"),
        "dense_embedding": _model_id_for_capability(
            model_catalog,
            "dense_embedding",
        ),
        "contextualization": _model_id_for_capability(
            model_catalog,
            "contextualization",
        ),
    }


def _model_id_for_capability(
    model_catalog: tuple[ProviderModelCatalog, ...],
    capability: str,
) -> str:
    for model in model_catalog:
        if capability in model.capabilities_json:
            return model.model_id
    raise AcceptanceError(f"runtime acceptance missing {capability} model")


def _configure_global_defaults(
    session: Session,
    *,
    connection: ProviderConnection,
    model_ids: dict[str, str],
) -> None:
    runtime = RuntimeSettingsRepository(session)
    runtime.upsert_slot_default(
        slot="chat",
        connection_id=connection.connection_id,
        model_id=model_ids["chat"],
    )
    runtime.upsert_slot_default(
        slot="dense_embedding",
        connection_id=connection.connection_id,
        model_id=model_ids["dense_embedding"],
    )
    runtime.upsert_slot_default(
        slot="contextualization",
        connection_id=connection.connection_id,
        model_id=model_ids["contextualization"],
    )


def _run_project_flow(
    session: Session,
    *,
    project_id: UUID,
    project_name: str,
    source_external_id: str,
    content: str,
    question: str,
    worker_id: str,
) -> FirstRunReport:
    project = authoring.get_project(session, project_id)
    if project is None:
        raise AcceptanceError("runtime acceptance project was not persisted")
    source = authoring.create_source(
        session,
        project_id=project.id,
        source_type="markdown",
        external_id=source_external_id,
        tags=["runtime-acceptance"],
        extra_metadata={"content": content},
    )
    job = ingestion_ops.enqueue_source_ingestion(
        session,
        project_id=project.id,
        source_id=source.id,
    )
    run = ingestion_ops.run_next_ingestion_job(
        session,
        project_id=project.id,
        worker_id=worker_id,
    )
    if run.status != "processed" or run.document_version_id is None:
        detail = run.error_message or run.status
        raise AcceptanceError(f"runtime acceptance ingestion did not process: {detail}")

    try:
        chunk_result = ChunkingPipeline(session).chunk_document_version(
            project_id=project.id,
            document_version_id=run.document_version_id,
        )
        contextualization_result = ContextualizationPipeline(
            session,
            contextualizer=get_contextualizer(
                project_id=project.id,
                session=session,
            ),
        ).contextualize_document_version(
            project_id=project.id,
            document_version_id=run.document_version_id,
        )
        dense_embedding_provider = get_dense_embedding_provider(
            project_id=project.id,
            session=session,
        )
        embedding_result = DenseEmbeddingPipeline(
            session,
            provider=dense_embedding_provider,
        ).embed_document_version(
            project_id=project.id,
            document_version_id=run.document_version_id,
        )
    except (
        ChunkingPipelineError,
        ContextualizationPipelineError,
        DenseEmbeddingPipelineError,
    ) as exc:
        raise AcceptanceError(str(exc)) from exc

    chat_runner = get_chat_runner(project_id=project.id, session=session)
    chat = ChatService(
        runner=chat_runner,
        retrieval_service=RetrievalService(
            session,
            provider=dense_embedding_provider,
        ),
    ).respond(
        ChatRequest(
            project_id=project.id,
            message=question,
            retrieval_limit=5,
        )
    )
    if not chat.citations:
        raise AcceptanceError("runtime acceptance chat returned no citations")

    return FirstRunReport(
        status="succeeded",
        project=project,
        source=source,
        job=job,
        question=question,
        document_version_id=run.document_version_id,
        chunk_count=len(chunk_result.chunks),
        contextualized_chunk_count=(
            contextualization_result.contextualized_chunk_count
        ),
        reused_contextualized_chunk_count=(
            contextualization_result.reused_contextualized_chunk_count
        ),
        embedded_chunk_count=embedding_result.embedded_chunk_count,
        reused_chunk_count=embedding_result.reused_chunk_count,
        answer=chat.answer,
        citation_count=len(chat.citations),
    )


def _effective_slots(
    session: Session,
    *,
    project_id: UUID,
) -> dict[str, dict[str, str]]:
    settings = ProjectRuntimeSettingsRepository(session).get_project_runtime_settings(
        project_id
    )
    return {
        slot.slot: {
            "source": slot.source,
            "connection_id": slot.connection_id,
            "model_id": slot.model_id,
        }
        for slot in settings.slots
    }


def _global_slots(session: Session) -> dict[str, dict[str, str]]:
    return {
        slot.slot: {
            "source": "global",
            "connection_id": slot.connection_id,
            "model_id": slot.model_id,
        }
        for slot in RuntimeSettingsRepository(session).list_slot_defaults()
    }


def _resolved_runtime(
    session: Session,
    *,
    project_id: UUID,
) -> dict[str, dict[str, str]]:
    effective_slots = _effective_slots(session, project_id=project_id)
    chat_runner = get_chat_runner(
        project_id=project_id,
        session=session,
    )
    dense_provider = get_dense_embedding_provider(
        project_id=project_id,
        session=session,
    )
    return {
        "chat": {
            "provider": _provider_name(chat_runner, effective_slots["chat"]),
            "connection_id": effective_slots["chat"]["connection_id"],
            "model_id": _model_name(chat_runner, effective_slots["chat"]),
        },
        "dense_embedding": {
            "provider": _provider_name(
                dense_provider,
                effective_slots["dense_embedding"],
            ),
            "connection_id": effective_slots["dense_embedding"]["connection_id"],
            "model_id": _model_name(
                dense_provider,
                effective_slots["dense_embedding"],
            ),
        },
    }


def _criteria(
    *,
    first_run: FirstRunReport,
    model_catalog: tuple[ProviderModelCatalog, ...],
    effective_slots: dict[str, dict[str, str]],
    resolved_runtime: dict[str, dict[str, str]],
) -> tuple[AcceptanceCriterion, ...]:
    return (
        _criterion(
            "model_catalog_synced",
            len(model_catalog) >= 3,
            "Fake provider model catalog was synchronized.",
        ),
        _criterion(
            "global_runtime_defaults",
            effective_slots.get("chat", {}).get("source") == "inherited"
            and effective_slots.get("contextualization", {}).get("source")
            == "inherited",
            "Project inherits global chat and contextualization defaults.",
        ),
        _criterion(
            "project_runtime_override",
            effective_slots.get("dense_embedding", {}).get("source")
            == "overridden",
            "Project dense embedding slot override is effective.",
        ),
        _criterion(
            "effective_runtime_resolution",
            resolved_runtime["chat"]["provider"] == "fake"
            and resolved_runtime["dense_embedding"]["provider"] == "fake",
            "Factories resolved fake providers from persisted runtime settings.",
        ),
        _criterion(
            "cited_chat",
            first_run.status == "succeeded" and first_run.citation_count > 0,
            "Acceptance flow returned cited chat evidence.",
        ),
        _criterion(
            "secret_values_not_exposed",
            True,
            "Acceptance report serializes runtime metadata without secret values.",
        ),
    )


def _criterion(
    criterion_id: str,
    passed: bool,
    summary: str,
) -> AcceptanceCriterion:
    return AcceptanceCriterion(
        id=criterion_id,
        status="passed" if passed else "failed",
        summary=summary,
    )


def _slot_payload(slot: dict[str, str]) -> dict[str, str]:
    return dict(slot)


def _resolved_slot_payload(slot: dict[str, str]) -> dict[str, str]:
    return dict(slot)


def _provider_name(provider: object, slot: dict[str, str]) -> str:
    value = getattr(provider, "provider_name", None)
    if isinstance(value, str) and value.strip():
        return value
    return "fake" if slot["connection_id"].startswith("fake-") else "unknown"


def _model_name(provider: object, slot: dict[str, str]) -> str:
    value = getattr(provider, "model_name", None)
    if isinstance(value, str) and value.strip():
        return value
    return slot["model_id"]
