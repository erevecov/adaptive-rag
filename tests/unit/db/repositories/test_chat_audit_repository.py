"""Tests para repositories M13 de audit trail de chat."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from adaptive_rag.chat import ChatRequest
from adaptive_rag.chat.audit import SqlAlchemyChatAuditWriter
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
    User,
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
from adaptive_rag.retrieval.payloads import RetrievalResultPayload


def _make_session():
    engine = create_engine_from_url("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(
        engine,
        tables=[
            Project.__table__,
            User.__table__,
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


def _make_user(session, login: str) -> User:
    user = User(login=login, display_name=login)
    session.add(user)
    session.flush()
    return user


def _make_chunk(session, *, project: Project, suffix: str = "") -> Chunk:
    source = SourceRepository(session).create(
        project_id=project.id,
        source_type="markdown",
        external_id=f"{project.name}{suffix}.md",
    )
    document = DocumentRepository(session).create_document(
        project_id=project.id,
        source_id=source.id,
        stable_id=f"{project.name}{suffix}-doc",
    )
    version = DocumentRepository(session).create_version(
        project_id=project.id,
        document_id=document.id,
        version_number=1,
        normalized_text="Alpha evidence",
        content_hash=f"sha256:{project.name}{suffix}",
        index_fingerprint=f"fp:{project.name}{suffix}",
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


def _set_session_timestamp(
    chat_session: ChatSession,
    created_at: datetime,
) -> None:
    chat_session.created_at = created_at
    chat_session.updated_at = created_at + timedelta(seconds=1)


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
        sparse_score=0.3,
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
    assert retrieved_chunks[0].sparse_score == 0.3
    assert retrieved_chunks[0].rrf_score == 0.2
    assert retrieved_chunks[0].rerank_score == 0.95
    assert retrieved_chunks[0].citation_json == {
        "chunk_id": str(chunk.id),
        "snippet": "Alpha evidence",
    }


def test_repository_scopes_session_history_to_owner_user() -> None:
    session = _make_session()
    project = _make_project(session, "demo")
    first_user = _make_user(session, "first@example.com")
    second_user = _make_user(session, "second@example.com")
    repo = ChatAuditRepository(session)
    first_session = repo.create_session(
        project_id=project.id,
        user_id=first_user.id,
    )
    second_session = repo.create_session(
        project_id=project.id,
        user_id=second_user.id,
    )
    session.commit()

    first_page = repo.list_session_summaries(
        project_id=project.id,
        user_id=first_user.id,
    )
    second_detail = repo.get_session_detail(
        project_id=project.id,
        session_id=second_session.id,
        user_id=first_user.id,
    )

    assert first_session.user_id == first_user.id
    assert [item.session_id for item in first_page.items] == [first_session.id]
    assert second_detail is None


def test_sqlalchemy_audit_writer_persists_retrieval_score_breakdown() -> None:
    session = _make_session()
    project = _make_project(session)
    chunk = _make_chunk(session, project=project)
    version = session.get(DocumentVersion, chunk.document_version_id)
    assert version is not None
    document = session.get(Document, version.document_id)
    assert document is not None
    source = session.get(Source, document.source_id)
    assert source is not None
    audit_repo = ChatAuditRepository(session)
    writer = SqlAlchemyChatAuditWriter(
        session=session,
        chat_audit_repository=audit_repo,
        provider_usage_repository=ProviderUsageRepository(session),
    )
    session_id = writer.start_session(
        ChatRequest(project_id=project.id, message="alpha"),
        "alpha",
    )
    tool_call_id = writer.start_retrieval_tool(
        project.id,
        session_id,
        "alpha",
        1,
        None,
        strategy="hybrid_rrf",
    )
    result: RetrievalResultPayload = {
        "chunk_id": str(chunk.id),
        "distance": 0.12,
        "score": 0.88,
        "citation": {
            "source_id": str(source.id),
            "source_type": "markdown",
            "source_external_id": "demo.md",
            "source_tags": [],
            "source_extra_metadata": None,
            "document_id": str(document.id),
            "document_stable_id": "demo-doc",
            "document_version_id": str(version.id),
            "document_version_number": 1,
            "chunk_id": str(chunk.id),
            "char_start": 0,
            "char_end": 14,
            "snippet": "Alpha evidence",
            "section_metadata": None,
        },
        "embedding_metadata": {"provider": "fake"},
        "strategy": "hybrid_rrf",
        "retrieval_metadata": {
            "dense_score": 0.88,
            "lexical_score": 3.0,
            "sparse_score": 2.0,
            "rrf_score": 0.03252247488101534,
            "dense_rank": 1,
            "lexical_rank": 2,
        },
        "rerank_metadata": {"rerank_score": 0.97},
    }

    writer.complete_retrieval_tool(
        project.id,
        session_id,
        tool_call_id,
        "alpha",
        1,
        None,
        8,
        [result],
        strategy="hybrid_rrf",
    )

    retrieval_runs = audit_repo.list_retrieval_runs(
        project_id=project.id,
        session_id=session_id,
    )
    retrieved_chunks = audit_repo.list_retrieved_chunks(
        project_id=project.id,
        retrieval_run_id=retrieval_runs[0].id,
    )
    assert retrieval_runs[0].strategy == "hybrid_rrf"
    assert retrieved_chunks[0].dense_score == 0.88
    assert retrieved_chunks[0].lexical_score == 3.0
    assert retrieved_chunks[0].sparse_score == 2.0
    assert retrieved_chunks[0].rrf_score == 0.03252247488101534
    assert retrieved_chunks[0].rerank_score == 0.97


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


def test_repository_lists_session_summaries_with_counts_filters_and_cursor() -> None:
    session = _make_session()
    project = _make_project(session, "demo")
    other_project = _make_project(session, "other")
    chunk = _make_chunk(session, project=project)
    other_chunk = _make_chunk(session, project=other_project)
    repo = ChatAuditRepository(session)
    usage_repo = ProviderUsageRepository(session)
    base_time = datetime(2026, 6, 21, 12, 0, tzinfo=UTC)

    older = repo.create_session(
        project_id=project.id,
        model_config_json={"provider": "fake", "model": "older"},
        prompt_version="history-v1",
    )
    _set_session_timestamp(older, base_time)
    repo.add_message(
        project_id=project.id,
        session_id=older.id,
        role="user",
        content="older question",
    )
    repo.succeed_session(project_id=project.id, session_id=older.id)

    middle = repo.create_session(
        project_id=project.id,
        model_config_json={"provider": "fake", "model": "middle"},
        prompt_version="history-v1",
    )
    _set_session_timestamp(middle, base_time + timedelta(minutes=1))
    middle_tool = repo.start_tool_call(
        project_id=project.id,
        session_id=middle.id,
        tool_name="retrieval.search",
        arguments_json={"query": "middle"},
    )
    middle_run = repo.create_retrieval_run(
        project_id=project.id,
        session_id=middle.id,
        tool_call_id=middle_tool.id,
        query="middle",
        strategy="dense",
        top_k=1,
        used_rerank=False,
    )
    repo.add_retrieved_chunk(
        project_id=project.id,
        retrieval_run_id=middle_run.id,
        chunk_id=chunk.id,
        rank=1,
        citation_json={"snippet": "middle evidence"},
    )
    usage_repo.create_from_record(
        project_id=project.id,
        session_id=middle.id,
        job_id=None,
        eval_run_id=None,
        record=_make_provider_call_record(),
    )
    repo.fail_session(
        project_id=project.id,
        session_id=middle.id,
        error_message="runner failed",
    )

    newest = repo.create_session(
        project_id=project.id,
        model_config_json={"provider": "fake", "model": "newest"},
    )
    _set_session_timestamp(newest, base_time + timedelta(minutes=2))
    repo.succeed_session(project_id=project.id, session_id=newest.id)

    other_session = repo.create_session(project_id=other_project.id)
    _set_session_timestamp(other_session, base_time + timedelta(minutes=3))
    other_run = repo.create_retrieval_run(
        project_id=other_project.id,
        session_id=other_session.id,
        tool_call_id=None,
        query="other",
        strategy="dense",
        top_k=1,
        used_rerank=False,
    )
    repo.add_retrieved_chunk(
        project_id=other_project.id,
        retrieval_run_id=other_run.id,
        chunk_id=other_chunk.id,
        rank=1,
        citation_json={"snippet": "other evidence"},
    )

    first_page = repo.list_session_summaries(project_id=project.id, limit=2)
    assert [item.session_id for item in first_page.items] == [newest.id, middle.id]
    assert first_page.next_cursor is not None
    assert first_page.items[1].status == "failed"
    assert first_page.items[1].model_config == {
        "provider": "fake",
        "model": "middle",
    }
    assert first_page.items[1].prompt_version == "history-v1"
    assert first_page.items[1].message_count == 0
    assert first_page.items[1].tool_call_count == 1
    assert first_page.items[1].retrieval_run_count == 1
    assert first_page.items[1].provider_usage_count == 1
    assert first_page.items[1].total_estimated_cost_usd == pytest.approx(0.0001)
    assert first_page.items[1].error_message == "runner failed"

    second_page = repo.list_session_summaries(
        project_id=project.id,
        limit=2,
        cursor=first_page.next_cursor,
    )
    assert [item.session_id for item in second_page.items] == [older.id]
    assert second_page.next_cursor is None

    failed_page = repo.list_session_summaries(
        project_id=project.id,
        status="failed",
        limit=10,
    )
    assert [item.session_id for item in failed_page.items] == [middle.id]


def test_repository_rejects_invalid_session_summary_options() -> None:
    session = _make_session()
    project = _make_project(session)
    repo = ChatAuditRepository(session)

    with pytest.raises(ValueError, match="limit must be between 1 and 100"):
        repo.list_session_summaries(project_id=project.id, limit=0)

    with pytest.raises(ValueError, match="invalid chat session status"):
        repo.list_session_summaries(project_id=project.id, status="archived")

    with pytest.raises(ValueError, match="invalid chat session cursor"):
        repo.list_session_summaries(project_id=project.id, cursor="not-a-cursor")


def test_repository_gets_session_detail_with_audit_records_and_project_scope() -> None:
    session = _make_session()
    project = _make_project(session, "demo")
    other_project = _make_project(session, "other")
    chunk = _make_chunk(session, project=project)
    repo = ChatAuditRepository(session)
    usage_repo = ProviderUsageRepository(session)
    chat_session = repo.create_session(
        project_id=project.id,
        model_config_json={"provider": "fake"},
        prompt_version="history-v1",
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
        arguments_json={"query": "alpha"},
    )
    repo.complete_tool_call(
        project_id=project.id,
        tool_call_id=tool_call.id,
        result_summary_json={"result_count": 2},
        latency_ms=5,
    )
    retrieval_run = repo.create_retrieval_run(
        project_id=project.id,
        session_id=chat_session.id,
        tool_call_id=tool_call.id,
        query="alpha",
        strategy="dense",
        top_k=2,
        used_rerank=True,
        filters_json={"source_type": "markdown"},
        latency_ms=5,
    )
    second_chunk = _make_chunk(session, project=project, suffix="-second")
    repo.add_retrieved_chunk(
        project_id=project.id,
        retrieval_run_id=retrieval_run.id,
        chunk_id=second_chunk.id,
        rank=2,
        citation_json={"snippet": "second"},
    )
    repo.add_retrieved_chunk(
        project_id=project.id,
        retrieval_run_id=retrieval_run.id,
        chunk_id=chunk.id,
        rank=1,
        citation_json={"snippet": "first"},
    )
    repo.add_message(
        project_id=project.id,
        session_id=chat_session.id,
        role="assistant",
        content="Alpha is supported.",
    )
    usage_repo.create_from_record(
        project_id=project.id,
        session_id=chat_session.id,
        job_id=None,
        eval_run_id=None,
        record=_make_provider_call_record(),
    )
    repo.succeed_session(project_id=project.id, session_id=chat_session.id)

    detail = repo.get_session_detail(
        project_id=project.id,
        session_id=chat_session.id,
    )

    assert detail is not None
    assert detail.session.id == chat_session.id
    assert [message.role for message in detail.messages] == ["user", "assistant"]
    assert detail.messages[0].metadata_json == {"retrieval_limit": 1}
    assert [item.id for item in detail.tool_calls] == [tool_call.id]
    assert detail.tool_calls[0].result_summary_json == {"result_count": 2}
    assert [item.id for item in detail.retrieval_runs] == [retrieval_run.id]
    assert detail.retrieval_runs[0].filters_json == {"source_type": "markdown"}
    assert [
        item.citation_json
        for item in detail.retrieved_chunks_by_run_id[retrieval_run.id]
    ] == [{"snippet": "first"}, {"snippet": "second"}]
    assert len(detail.provider_usage) == 1
    assert detail.provider_usage[0].provider == "qwen"

    assert (
        repo.get_session_detail(
            project_id=other_project.id,
            session_id=chat_session.id,
        )
        is None
    )
