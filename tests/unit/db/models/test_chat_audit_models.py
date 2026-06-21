"""Tests para modelos M13 de audit trail de chat."""

from __future__ import annotations

from sqlalchemy import inspect, select
from sqlalchemy.exc import IntegrityError

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
    ChunkRepository,
    DocumentRepository,
    ProjectRepository,
    SourceRepository,
)
from adaptive_rag.db.session import create_engine_from_url, create_session_factory


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


def _make_project(session) -> Project:
    return ProjectRepository(session).create(name="demo")


def _make_chunk(session, *, project: Project) -> Chunk:
    source = SourceRepository(session).create(
        project_id=project.id,
        source_type="markdown",
        external_id="alpha.md",
    )
    document = DocumentRepository(session).create_document(
        project_id=project.id,
        source_id=source.id,
        stable_id="alpha-doc",
    )
    version = DocumentRepository(session).create_version(
        project_id=project.id,
        document_id=document.id,
        version_number=1,
        normalized_text="Alpha evidence",
        content_hash="sha256:alpha",
        index_fingerprint="fp:alpha",
    )
    return ChunkRepository(session).create(
        project_id=project.id,
        document_version_id=version.id,
        ordinal=0,
        char_start=0,
        char_end=14,
        token_count=2,
    )


def test_chat_session_defaults_to_running() -> None:
    session = _make_session()
    project = _make_project(session)
    chat_session = ChatSession(project_id=project.id)

    session.add(chat_session)
    session.commit()

    assert chat_session.status == "running"
    assert chat_session.created_at is not None
    assert chat_session.updated_at is not None


def test_chat_message_persists_role_content_and_metadata() -> None:
    session = _make_session()
    project = _make_project(session)
    chat_session = ChatSession(project_id=project.id)
    session.add(chat_session)
    session.flush()
    message = ChatMessage(
        project_id=project.id,
        session_id=chat_session.id,
        role="user",
        content="What supports alpha?",
        metadata_json={"retrieval_limit": 2},
    )

    session.add(message)
    session.commit()
    session.expunge_all()

    fetched = session.execute(select(ChatMessage)).scalar_one()
    assert fetched.project_id == project.id
    assert fetched.session_id == chat_session.id
    assert fetched.role == "user"
    assert fetched.content == "What supports alpha?"
    assert fetched.metadata_json == {"retrieval_limit": 2}


def test_invalid_statuses_and_roles_are_rejected() -> None:
    session = _make_session()
    project = _make_project(session)
    chat_session = ChatSession(project_id=project.id, status="bogus")
    session.add(chat_session)

    try:
        session.commit()
    except IntegrityError:
        session.rollback()
    else:
        raise AssertionError("Expected IntegrityError for invalid chat status")

    valid_session = ChatSession(project_id=project.id)
    session.add(valid_session)
    session.flush()
    session.add(
        ChatMessage(
            project_id=project.id,
            session_id=valid_session.id,
            role="bogus",
            content="bad role",
        )
    )

    try:
        session.commit()
    except IntegrityError:
        session.rollback()
    else:
        raise AssertionError("Expected IntegrityError for invalid message role")


def test_retrieval_run_and_retrieved_chunk_persist_citation_payload() -> None:
    session = _make_session()
    project = _make_project(session)
    chunk = _make_chunk(session, project=project)
    chat_session = ChatSession(project_id=project.id)
    session.add(chat_session)
    session.flush()
    tool_call = ToolCall(
        project_id=project.id,
        session_id=chat_session.id,
        tool_name="retrieval.search",
        arguments_json={"query": "alpha", "limit": 1},
    )
    session.add(tool_call)
    session.flush()
    retrieval_run = RetrievalRun(
        project_id=project.id,
        session_id=chat_session.id,
        tool_call_id=tool_call.id,
        query="alpha",
        strategy="dense",
        top_k=1,
        used_rerank=False,
        filters_json={"source_type": "markdown"},
    )
    session.add(retrieval_run)
    session.flush()
    retrieved = RetrievedChunk(
        project_id=project.id,
        retrieval_run_id=retrieval_run.id,
        chunk_id=chunk.id,
        rank=1,
        dense_score=0.9,
        citation_json={"chunk_id": str(chunk.id), "snippet": "Alpha evidence"},
    )

    session.add(retrieved)
    session.commit()
    session.expunge_all()

    fetched = session.execute(select(RetrievedChunk)).scalar_one()
    assert fetched.rank == 1
    assert fetched.dense_score == 0.9
    assert fetched.citation_json == {
        "chunk_id": str(chunk.id),
        "snippet": "Alpha evidence",
    }


def test_provider_usage_can_link_to_session_job_or_eval_context() -> None:
    session = _make_session()
    project = _make_project(session)
    chat_session = ChatSession(project_id=project.id)
    job = Job(project_id=project.id, job_type="ingest_url")
    session.add_all([chat_session, job])
    session.flush()
    usage = ProviderUsage(
        project_id=project.id,
        session_id=chat_session.id,
        job_id=job.id,
        eval_run_id=None,
        operation="chat",
        provider="qwen",
        model="qwen-plus",
        status="succeeded",
        usage_source="provider_reported",
        input_tokens=10,
        output_tokens=5,
        total_tokens=15,
        estimated_cost_usd=0.0001,
        currency="USD",
        latency_ms=123,
    )

    session.add(usage)
    session.commit()

    assert usage.id is not None
    assert usage.session_id == chat_session.id
    assert usage.job_id == job.id


def test_audit_tables_have_project_session_indexes() -> None:
    table_indexes = {
        ChatSession.__tablename__: inspect(ChatSession).local_table.indexes,
        ChatMessage.__tablename__: inspect(ChatMessage).local_table.indexes,
        ToolCall.__tablename__: inspect(ToolCall).local_table.indexes,
        RetrievalRun.__tablename__: inspect(RetrievalRun).local_table.indexes,
        RetrievedChunk.__tablename__: inspect(RetrievedChunk).local_table.indexes,
        ProviderUsage.__tablename__: inspect(ProviderUsage).local_table.indexes,
    }

    indexed_columns = {
        table_name: {
            tuple(column.name for column in index.columns) for index in indexes
        }
        for table_name, indexes in table_indexes.items()
    }

    assert ("project_id", "created_at") in indexed_columns["chat_sessions"]
    assert ("project_id", "session_id", "created_at") in indexed_columns[
        "chat_messages"
    ]
    assert ("project_id", "session_id", "created_at") in indexed_columns[
        "tool_calls"
    ]
    assert ("project_id", "session_id", "created_at") in indexed_columns[
        "retrieval_runs"
    ]
    assert ("project_id", "retrieval_run_id", "rank") in indexed_columns[
        "retrieved_chunks"
    ]
    assert ("project_id", "session_id", "created_at") in indexed_columns[
        "provider_usage"
    ]
