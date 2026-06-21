"""Tests para repositories M13 de audit trail de chat."""

from __future__ import annotations

import pytest

from adaptive_rag.db.base import Base
from adaptive_rag.db.models import (
    ChatMessage,
    ChatSession,
    Chunk,
    Document,
    DocumentVersion,
    Job,
    Project,
    ProviderUsage,
    RetrievalRun,
    RetrievedChunk,
    Source,
    ToolCall,
)
from adaptive_rag.db.repositories import (
    ChatAuditRepository,
    ChunkRepository,
    DocumentRepository,
    ProjectRepository,
    ProviderUsageRepository,
    SourceRepository,
)
from adaptive_rag.db.session import create_engine_from_url, create_session_factory
from adaptive_rag.provider_usage import ProviderCallRecord, ProviderTokenUsage


def _make_session():
    engine = create_engine_from_url("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(
        engine,
        tables=[
            Project.__table__,
            Source.__table__,
            Document.__table__,
            DocumentVersion.__table__,
            Chunk.__table__,
            Job.__table__,
            ChatSession.__table__,
            ChatMessage.__table__,
            ToolCall.__table__,
            RetrievalRun.__table__,
            RetrievedChunk.__table__,
            ProviderUsage.__table__,
        ],
    )
    return create_session_factory(engine)()


def _make_project(session, name: str = "demo") -> Project:
    return ProjectRepository(session).create(name=name)


def _make_chunk(session, *, project: Project) -> Chunk:
    source = SourceRepository(session).create(
        project_id=project.id,
        source_type="markdown",
        external_id=f"{project.name}.md",
    )
    document = DocumentRepository(session).create_document(
        project_id=project.id,
        source_id=source.id,
        stable_id=f"{project.name}-doc",
    )
    version = DocumentRepository(session).create_version(
        project_id=project.id,
        document_id=document.id,
        version_number=1,
        normalized_text="Alpha evidence",
        content_hash=f"sha256:{project.name}",
        index_fingerprint=f"fp:{project.name}",
    )
    return ChunkRepository(session).create(
        project_id=project.id,
        document_version_id=version.id,
        ordinal=0,
        char_start=0,
        char_end=14,
        token_count=2,
    )


def _make_provider_call_record() -> ProviderCallRecord:
    return ProviderCallRecord(
        provider="qwen",
        model="qwen-plus",
        operation="chat",
        outcome="succeeded",
        duration_ms=25,
        usage=ProviderTokenUsage(
            input_tokens=10,
            output_tokens=5,
            total_tokens=15,
            input_count=1,
        ),
        usage_source="provider_reported",
        estimated_cost_usd=0.0001,
        request_id="req-123",
        error_type="RateLimitError",
    )


def test_repository_creates_session_messages_tool_and_retrieval_run() -> None:
    session = _make_session()
    project = _make_project(session)
    chunk = _make_chunk(session, project=project)
    repo = ChatAuditRepository(session)

    chat_session = repo.create_session(
        project_id=project.id,
        model_config_json={"provider": "fake"},
        prompt_version="tool_selection_v1",
    )
    repo.add_message(
        project_id=project.id,
        session_id=chat_session.id,
        role="user",
        content="What supports alpha?",
        metadata_json={"retrieval_limit": 1},
    )
    tool_call = repo.start_tool_call(
        project_id=project.id,
        session_id=chat_session.id,
        tool_name="retrieval.search",
        arguments_json={"query": "alpha", "limit": 1},
    )
    repo.complete_tool_call(
        project_id=project.id,
        tool_call_id=tool_call.id,
        result_summary_json={"result_count": 1},
        latency_ms=7,
    )
    retrieval_run = repo.create_retrieval_run(
        project_id=project.id,
        session_id=chat_session.id,
        tool_call_id=tool_call.id,
        query="alpha",
        strategy="dense",
        top_k=1,
        used_rerank=False,
        filters_json={"source_type": "markdown"},
        latency_ms=7,
    )
    repo.add_retrieved_chunk(
        project_id=project.id,
        retrieval_run_id=retrieval_run.id,
        chunk_id=chunk.id,
        rank=1,
        dense_score=0.9,
        lexical_score=0.4,
        rrf_score=0.2,
        rerank_score=0.95,
        citation_json={"chunk_id": str(chunk.id), "snippet": "Alpha evidence"},
    )
    repo.add_message(
        project_id=project.id,
        session_id=chat_session.id,
        role="assistant",
        content="Alpha evidence",
    )
    repo.succeed_session(project_id=project.id, session_id=chat_session.id)

    messages = repo.list_messages(project_id=project.id, session_id=chat_session.id)
    tool_calls = repo.list_tool_calls(
        project_id=project.id,
        session_id=chat_session.id,
    )
    retrieval_runs = repo.list_retrieval_runs(
        project_id=project.id,
        session_id=chat_session.id,
    )
    retrieved_chunks = repo.list_retrieved_chunks(
        project_id=project.id,
        retrieval_run_id=retrieval_run.id,
    )

    assert chat_session.status == "succeeded"
    assert [message.role for message in messages] == ["user", "assistant"]
    assert tool_calls[0].status == "succeeded"
    assert retrieval_runs[0].query == "alpha"
    assert retrieved_chunks[0].dense_score == 0.9
    assert retrieved_chunks[0].lexical_score == 0.4
    assert retrieved_chunks[0].rrf_score == 0.2
    assert retrieved_chunks[0].rerank_score == 0.95
    assert retrieved_chunks[0].citation_json == {
        "chunk_id": str(chunk.id),
        "snippet": "Alpha evidence",
    }


def test_repository_scopes_reads_and_writes_by_project() -> None:
    session = _make_session()
    project = _make_project(session, "demo")
    other_project = _make_project(session, "other")
    chunk = _make_chunk(session, project=project)
    other_chunk = _make_chunk(session, project=other_project)
    repo = ChatAuditRepository(session)
    chat_session = repo.create_session(project_id=project.id)
    tool_call = repo.start_tool_call(
        project_id=project.id,
        session_id=chat_session.id,
        tool_name="retrieval.search",
        arguments_json={"query": "alpha"},
    )
    retrieval_run = repo.create_retrieval_run(
        project_id=project.id,
        session_id=chat_session.id,
        tool_call_id=tool_call.id,
        query="alpha",
        strategy="dense",
        top_k=1,
        used_rerank=False,
    )

    assert (
        repo.get_session(project_id=other_project.id, session_id=chat_session.id)
        is None
    )
    with pytest.raises(ValueError, match="chunk does not belong to project"):
        repo.add_retrieved_chunk(
            project_id=project.id,
            retrieval_run_id=retrieval_run.id,
            chunk_id=other_chunk.id,
            rank=1,
            citation_json={"chunk_id": str(other_chunk.id)},
        )

    repo.add_retrieved_chunk(
        project_id=project.id,
        retrieval_run_id=retrieval_run.id,
        chunk_id=chunk.id,
        rank=1,
        citation_json={"chunk_id": str(chunk.id)},
    )
    assert (
        repo.list_retrieved_chunks(
            project_id=other_project.id,
            retrieval_run_id=retrieval_run.id,
        )
        == []
    )


def test_repository_marks_failed_session_and_tool_call() -> None:
    session = _make_session()
    project = _make_project(session)
    repo = ChatAuditRepository(session)
    chat_session = repo.create_session(project_id=project.id)
    tool_call = repo.start_tool_call(
        project_id=project.id,
        session_id=chat_session.id,
        tool_name="retrieval.search",
        arguments_json={"query": "alpha"},
    )

    failed_tool = repo.fail_tool_call(
        project_id=project.id,
        tool_call_id=tool_call.id,
        error_message="query must not be empty",
        latency_ms=3,
    )
    failed_session = repo.fail_session(
        project_id=project.id,
        session_id=chat_session.id,
        error_message="query must not be empty",
    )

    assert failed_tool.status == "failed"
    assert failed_tool.error_message == "query must not be empty"
    assert failed_session.status == "failed"
    assert failed_session.error_message == "query must not be empty"


def test_repository_rejects_tool_call_from_different_session() -> None:
    session = _make_session()
    project = _make_project(session)
    repo = ChatAuditRepository(session)
    first_session = repo.create_session(project_id=project.id)
    second_session = repo.create_session(project_id=project.id)
    tool_call = repo.start_tool_call(
        project_id=project.id,
        session_id=first_session.id,
        tool_name="retrieval.search",
        arguments_json={"query": "alpha"},
    )

    with pytest.raises(ValueError, match="tool call does not belong to session"):
        repo.create_retrieval_run(
            project_id=project.id,
            session_id=second_session.id,
            tool_call_id=tool_call.id,
            query="alpha",
            strategy="dense",
            top_k=1,
            used_rerank=False,
        )


def test_provider_usage_repository_persists_provider_call_record() -> None:
    session = _make_session()
    project = _make_project(session)
    repo = ChatAuditRepository(session)
    usage_repo = ProviderUsageRepository(session)
    chat_session = repo.create_session(project_id=project.id)

    usage = usage_repo.create_from_record(
        project_id=project.id,
        session_id=chat_session.id,
        job_id=None,
        eval_run_id=None,
        record=_make_provider_call_record(),
    )

    assert usage.provider == "qwen"
    assert usage.model == "qwen-plus"
    assert usage.operation == "chat"
    assert usage.status == "succeeded"
    assert usage.input_tokens == 10
    assert usage.output_tokens == 5
    assert usage.total_tokens == 15
    assert usage.input_count == 1
    assert usage.provider_request_id == "req-123"
    assert usage.error_message == "RateLimitError"


def test_provider_usage_repository_rejects_wrong_project_session() -> None:
    session = _make_session()
    project = _make_project(session, "demo")
    other_project = _make_project(session, "other")
    repo = ChatAuditRepository(session)
    usage_repo = ProviderUsageRepository(session)
    other_session = repo.create_session(project_id=other_project.id)

    with pytest.raises(ValueError, match="chat session does not belong to project"):
        usage_repo.create_from_record(
            project_id=project.id,
            session_id=other_session.id,
            job_id=None,
            eval_run_id=None,
            record=_make_provider_call_record(),
        )


def test_provider_usage_repository_rejects_wrong_project_job() -> None:
    session = _make_session()
    project = _make_project(session, "demo")
    other_project = _make_project(session, "other")
    usage_repo = ProviderUsageRepository(session)
    other_job = Job(project_id=other_project.id, job_type="chat")
    session.add(other_job)
    session.flush()

    with pytest.raises(ValueError, match="job does not belong to project"):
        usage_repo.create_from_record(
            project_id=project.id,
            session_id=None,
            job_id=other_job.id,
            eval_run_id=None,
            record=_make_provider_call_record(),
        )


def test_provider_usage_repository_persists_job_only_context() -> None:
    session = _make_session()
    project = _make_project(session)
    usage_repo = ProviderUsageRepository(session)
    job = Job(project_id=project.id, job_type="chat")
    session.add(job)
    session.flush()

    usage = usage_repo.create_from_record(
        project_id=project.id,
        session_id=None,
        job_id=job.id,
        eval_run_id=None,
        record=_make_provider_call_record(),
    )

    assert usage.session_id is None
    assert usage.job_id == job.id
    assert usage.project_id == project.id
