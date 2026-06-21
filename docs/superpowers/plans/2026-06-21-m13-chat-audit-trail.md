# M13 Chat Audit Trail Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build M13 durable chat audit trail so each valid chat run can persist session, messages, tool calls, retrieval runs, retrieved citations, and provider usage context.

**Architecture:** Add SQLAlchemy/Alembic persistence first, then repositories, then a small chat audit writer injected into `ChatService`. API and CLI stay thin adapters; provider usage linking uses a request-scoped in-memory tracker that is flushed into durable `provider_usage` rows after the chat run has a `session_id`.

**Tech Stack:** Python 3.12, SQLAlchemy 2, Alembic, FastAPI, Typer, Pydantic v2, pytest, Ruff, mypy, OpenSpec.

---

## Scope Lock

This plan implements the active OpenSpec change `openspec/changes/m13-chat-audit-trail/`.

Included:

- Durable chat audit schema.
- Repositories with `project_id` isolation.
- Optional audit writer injected into `ChatService`.
- API/CLI persistence with compatible response payloads plus optional `session_id`.
- Provider usage rows linked to `session_id`, `job_id`, or `eval_run_id` when context exists.
- Tests with fakes and SQLite unless an existing contract already needs Postgres.

Excluded:

- Streaming SSE.
- Session history/list endpoints or CLI commands.
- Dashboards.
- OpenTelemetry exporter.
- Retrieval ranking changes, lexical/RRF, sparse retrieval, or new defaults.

## File Structure

Create:

- `alembic/versions/b7a3c9d4e5f6_m13_chat_audit_trail.py`: migration for all M13 audit tables.
- `src/adaptive_rag/db/models/chat_session.py`: chat session model and status values.
- `src/adaptive_rag/db/models/chat_message.py`: chat message model and role values.
- `src/adaptive_rag/db/models/tool_call.py`: tool call model and status values.
- `src/adaptive_rag/db/models/retrieval_run.py`: retrieval run model.
- `src/adaptive_rag/db/models/retrieved_chunk.py`: retrieved chunk audit model.
- `src/adaptive_rag/db/models/provider_usage.py`: durable provider usage model.
- `src/adaptive_rag/db/repositories/chat_audit.py`: repositories for sessions, messages, tool calls, retrieval runs, retrieved chunks, and provider usage.
- `src/adaptive_rag/chat/audit.py`: chat-layer audit writer protocol, null writer, SQLAlchemy writer, and metadata helpers.
- `tests/unit/db/models/test_chat_audit_models.py`: schema/model tests.
- `tests/unit/db/repositories/test_chat_audit_repository.py`: repository tests.
- `tests/unit/chat/test_chat_audit_wiring.py`: chat service audit tests.

Modify:

- `src/adaptive_rag/db/models/__init__.py`: export new models and constants.
- `src/adaptive_rag/db/repositories/__init__.py`: export new repositories.
- `src/adaptive_rag/chat/models.py`: add optional `session_id` to `ChatResponse`.
- `src/adaptive_rag/chat/payloads.py`: serialize `session_id` when present.
- `src/adaptive_rag/chat/tools.py`: allow retrieval tool to notify audit writer.
- `src/adaptive_rag/chat/service.py`: start/succeed/fail audit sessions around runner execution.
- `src/adaptive_rag/chat/__init__.py`: export audit writer types if needed by dependencies.
- `src/adaptive_rag/api/dependencies.py`: construct request-scoped audit writer and usage tracker.
- `src/adaptive_rag/api/schemas/chat.py`: expose optional `session_id`.
- `src/adaptive_rag/cli/chat.py`: create audit writer and usage tracker inside `session_scope()`.
- `src/adaptive_rag/cli/dependencies.py`: add helper that can build hosted/live runtime with a supplied usage tracker when needed.
- `tests/integration/api/test_chat.py`: assert audit rows are persisted.
- `tests/integration/cli/test_chat_cli.py`: assert CLI persists audit rows.
- `openspec/changes/m13-chat-audit-trail/tasks.md`: mark implementation tasks as completed as they land.
- `docs/progress.md` and `docs/roadmap.md`: update only during quality gate or milestone closeout.

---

### Task 1: Audit Schema and SQLAlchemy Models

**Files:**

- Create: `alembic/versions/b7a3c9d4e5f6_m13_chat_audit_trail.py`
- Create: `src/adaptive_rag/db/models/chat_session.py`
- Create: `src/adaptive_rag/db/models/chat_message.py`
- Create: `src/adaptive_rag/db/models/tool_call.py`
- Create: `src/adaptive_rag/db/models/retrieval_run.py`
- Create: `src/adaptive_rag/db/models/retrieved_chunk.py`
- Create: `src/adaptive_rag/db/models/provider_usage.py`
- Modify: `src/adaptive_rag/db/models/__init__.py`
- Test: `tests/unit/db/models/test_chat_audit_models.py`

- [ ] **Step 1: Write the failing model tests**

Create `tests/unit/db/models/test_chat_audit_models.py`:

```python
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
    RetrievedChunk,
    RetrievalRun,
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

    fetched = session.scalars(select(ChatMessage)).one()
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

    fetched = session.scalars(select(RetrievedChunk)).one()
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
        table_name: {tuple(column.name for column in index.columns) for index in indexes}
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
```

- [ ] **Step 2: Run the model tests and verify they fail**

Run:

```powershell
uv run pytest tests/unit/db/models/test_chat_audit_models.py -q
```

Expected: FAIL during import because `ChatSession`, `ChatMessage`, `ToolCall`, `RetrievalRun`, `RetrievedChunk`, and `ProviderUsage` are not exported yet.

- [ ] **Step 3: Add SQLAlchemy models**

Create `src/adaptive_rag/db/models/chat_session.py`:

```python
"""Modelo ChatSession: corrida conversacional auditable por proyecto."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from adaptive_rag.db.base import Base
from adaptive_rag.db.models.job import utc_now
from adaptive_rag.db.models.project import JSONWithJSONB

CHAT_SESSION_STATUS_VALUES = ("running", "succeeded", "failed")


class ChatSession(Base):
    """Sesion de chat persistida para audit trail."""

    __tablename__ = "chat_sessions"
    __table_args__ = (
        CheckConstraint(
            "status IN ('running', 'succeeded', 'failed')",
            name="chat_sessions_status_check",
        ),
        Index("ix_chat_sessions_project_created_at", "project_id", "created_at"),
        Index("ix_chat_sessions_project_status", "project_id", "status"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    project_id: Mapped[UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(
        nullable=False, default="running", server_default="running"
    )
    model_config_json: Mapped[dict[str, Any] | None] = mapped_column(
        JSONWithJSONB(), nullable=True
    )
    prompt_version: Mapped[str | None] = mapped_column(nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
```

Create `src/adaptive_rag/db/models/chat_message.py`:

```python
"""Modelo ChatMessage: mensajes persistidos de una sesion de chat."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from adaptive_rag.db.base import Base
from adaptive_rag.db.models.job import utc_now
from adaptive_rag.db.models.project import JSONWithJSONB

CHAT_MESSAGE_ROLE_VALUES = ("user", "assistant")


class ChatMessage(Base):
    """Mensaje de usuario o assistant asociado a una sesion auditable."""

    __tablename__ = "chat_messages"
    __table_args__ = (
        CheckConstraint(
            "role IN ('user', 'assistant')",
            name="chat_messages_role_check",
        ),
        Index(
            "ix_chat_messages_project_session_created_at",
            "project_id",
            "session_id",
            "created_at",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    project_id: Mapped[UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    session_id: Mapped[UUID] = mapped_column(
        ForeignKey("chat_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role: Mapped[str] = mapped_column(nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(
        JSONWithJSONB(), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        server_default=func.now(),
        nullable=False,
    )
```

Create `src/adaptive_rag/db/models/tool_call.py`:

```python
"""Modelo ToolCall: llamada de tool ejecutada durante chat."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from adaptive_rag.db.base import Base
from adaptive_rag.db.models.job import utc_now
from adaptive_rag.db.models.project import JSONWithJSONB

TOOL_CALL_STATUS_VALUES = ("running", "succeeded", "failed")


class ToolCall(Base):
    """Audit trail de una llamada de tool."""

    __tablename__ = "tool_calls"
    __table_args__ = (
        CheckConstraint(
            "status IN ('running', 'succeeded', 'failed')",
            name="tool_calls_status_check",
        ),
        CheckConstraint(
            "latency_ms IS NULL OR latency_ms >= 0",
            name="tool_calls_latency_non_negative_check",
        ),
        Index(
            "ix_tool_calls_project_session_created_at",
            "project_id",
            "session_id",
            "created_at",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    project_id: Mapped[UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    session_id: Mapped[UUID] = mapped_column(
        ForeignKey("chat_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tool_name: Mapped[str] = mapped_column(nullable=False)
    arguments_json: Mapped[dict[str, Any] | None] = mapped_column(
        JSONWithJSONB(), nullable=True
    )
    result_summary_json: Mapped[dict[str, Any] | None] = mapped_column(
        JSONWithJSONB(), nullable=True
    )
    status: Mapped[str] = mapped_column(
        nullable=False, default="running", server_default="running"
    )
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
```

Create `src/adaptive_rag/db/models/retrieval_run.py`:

```python
"""Modelo RetrievalRun: ejecucion de retrieval asociada a chat/tool."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from adaptive_rag.db.base import Base
from adaptive_rag.db.models.job import utc_now
from adaptive_rag.db.models.project import JSONWithJSONB


class RetrievalRun(Base):
    """Audit trail de una busqueda retrieval ejecutada durante chat."""

    __tablename__ = "retrieval_runs"
    __table_args__ = (
        CheckConstraint("top_k > 0", name="retrieval_runs_top_k_positive_check"),
        CheckConstraint(
            "latency_ms IS NULL OR latency_ms >= 0",
            name="retrieval_runs_latency_non_negative_check",
        ),
        Index(
            "ix_retrieval_runs_project_session_created_at",
            "project_id",
            "session_id",
            "created_at",
        ),
        Index("ix_retrieval_runs_project_strategy", "project_id", "strategy"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    project_id: Mapped[UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    session_id: Mapped[UUID] = mapped_column(
        ForeignKey("chat_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tool_call_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("tool_calls.id", ondelete="SET NULL"), nullable=True, index=True
    )
    query: Mapped[str] = mapped_column(Text, nullable=False)
    strategy: Mapped[str] = mapped_column(
        nullable=False, default="dense", server_default="dense"
    )
    top_k: Mapped[int] = mapped_column(Integer, nullable=False)
    used_rerank: Mapped[bool] = mapped_column(
        nullable=False, default=False, server_default="false"
    )
    filters_json: Mapped[dict[str, Any] | None] = mapped_column(
        JSONWithJSONB(), nullable=True
    )
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        server_default=func.now(),
        nullable=False,
    )
```

Create `src/adaptive_rag/db/models/retrieved_chunk.py`:

```python
"""Modelo RetrievedChunk: resultado citabled de un retrieval run."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from adaptive_rag.db.base import Base
from adaptive_rag.db.models.job import utc_now
from adaptive_rag.db.models.project import JSONWithJSONB


class RetrievedChunk(Base):
    """Chunk recuperado y citation persistida para audit trail."""

    __tablename__ = "retrieved_chunks"
    __table_args__ = (
        UniqueConstraint(
            "retrieval_run_id",
            "rank",
            name="uq_retrieved_chunks_run_rank",
        ),
        CheckConstraint("rank > 0", name="retrieved_chunks_rank_positive_check"),
        Index(
            "ix_retrieved_chunks_project_retrieval_run_rank",
            "project_id",
            "retrieval_run_id",
            "rank",
        ),
        Index("ix_retrieved_chunks_project_chunk", "project_id", "chunk_id"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    project_id: Mapped[UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    retrieval_run_id: Mapped[UUID] = mapped_column(
        ForeignKey("retrieval_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    chunk_id: Mapped[UUID] = mapped_column(
        ForeignKey("chunks.id", ondelete="CASCADE"), nullable=False, index=True
    )
    rank: Mapped[int] = mapped_column(Integer, nullable=False)
    dense_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    lexical_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    rrf_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    rerank_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    citation_json: Mapped[dict[str, Any]] = mapped_column(
        JSONWithJSONB(), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        server_default=func.now(),
        nullable=False,
    )
```

Create `src/adaptive_rag/db/models/provider_usage.py`:

```python
"""Modelo ProviderUsage: usage/costo durable de llamadas provider."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, Float, ForeignKey, Index, Integer, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from adaptive_rag.db.base import Base
from adaptive_rag.db.models.job import utc_now

PROVIDER_USAGE_OPERATION_VALUES = (
    "chat",
    "contextualize",
    "embedding",
    "rerank",
    "eval_judge",
)
PROVIDER_USAGE_STATUS_VALUES = ("succeeded", "failed", "blocked")
PROVIDER_USAGE_SOURCE_VALUES = (
    "provider_reported",
    "estimated",
    "unavailable",
)


class ProviderUsage(Base):
    """Registro durable de usage/costo sin secretos."""

    __tablename__ = "provider_usage"
    __table_args__ = (
        CheckConstraint(
            "operation IN ('chat', 'contextualize', 'embedding', 'rerank', "
            "'eval_judge')",
            name="provider_usage_operation_check",
        ),
        CheckConstraint(
            "status IN ('succeeded', 'failed', 'blocked')",
            name="provider_usage_status_check",
        ),
        CheckConstraint(
            "usage_source IN ('provider_reported', 'estimated', 'unavailable')",
            name="provider_usage_source_check",
        ),
        CheckConstraint(
            "input_tokens IS NULL OR input_tokens >= 0",
            name="provider_usage_input_tokens_non_negative_check",
        ),
        CheckConstraint(
            "output_tokens IS NULL OR output_tokens >= 0",
            name="provider_usage_output_tokens_non_negative_check",
        ),
        CheckConstraint(
            "total_tokens IS NULL OR total_tokens >= 0",
            name="provider_usage_total_tokens_non_negative_check",
        ),
        CheckConstraint(
            "input_count IS NULL OR input_count >= 0",
            name="provider_usage_input_count_non_negative_check",
        ),
        CheckConstraint(
            "latency_ms IS NULL OR latency_ms >= 0",
            name="provider_usage_latency_non_negative_check",
        ),
        Index(
            "ix_provider_usage_project_session_created_at",
            "project_id",
            "session_id",
            "created_at",
        ),
        Index(
            "ix_provider_usage_project_operation_created_at",
            "project_id",
            "operation",
            "created_at",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    project_id: Mapped[UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    session_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("chat_sessions.id", ondelete="SET NULL"), nullable=True, index=True
    )
    job_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("jobs.id", ondelete="SET NULL"), nullable=True, index=True
    )
    eval_run_id: Mapped[UUID | None] = mapped_column(nullable=True, index=True)
    operation: Mapped[str] = mapped_column(nullable=False)
    provider: Mapped[str] = mapped_column(nullable=False)
    model: Mapped[str] = mapped_column(nullable=False)
    provider_request_id: Mapped[str | None] = mapped_column(nullable=True)
    price_snapshot_id: Mapped[str | None] = mapped_column(nullable=True)
    input_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    output_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    input_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    usage_source: Mapped[str] = mapped_column(nullable=False)
    estimated_cost_usd: Mapped[float | None] = mapped_column(Float, nullable=True)
    currency: Mapped[str] = mapped_column(nullable=False, default="USD", server_default="USD")
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        server_default=func.now(),
        nullable=False,
    )
```

Modify `src/adaptive_rag/db/models/__init__.py` to import and export all new classes and constants:

```python
from adaptive_rag.db.models.chat_message import CHAT_MESSAGE_ROLE_VALUES, ChatMessage
from adaptive_rag.db.models.chat_session import CHAT_SESSION_STATUS_VALUES, ChatSession
from adaptive_rag.db.models.provider_usage import (
    PROVIDER_USAGE_OPERATION_VALUES,
    PROVIDER_USAGE_SOURCE_VALUES,
    PROVIDER_USAGE_STATUS_VALUES,
    ProviderUsage,
)
from adaptive_rag.db.models.retrieval_run import RetrievalRun
from adaptive_rag.db.models.retrieved_chunk import RetrievedChunk
from adaptive_rag.db.models.tool_call import TOOL_CALL_STATUS_VALUES, ToolCall
```

Add the imported names to `__all__`.

- [ ] **Step 4: Add Alembic migration**

Create `alembic/versions/b7a3c9d4e5f6_m13_chat_audit_trail.py` with `down_revision = "d3f6d8a1a9b2"`. Use the same columns, constraints, and indexes as the models. Drop tables in reverse order in `downgrade()`:

```python
"""m13 chat audit trail

Revision ID: b7a3c9d4e5f6
Revises: d3f6d8a1a9b2
Create Date: 2026-06-21 00:00:00.000000

Agrega audit trail durable para sesiones de chat, mensajes, tool calls,
retrieval runs, retrieved chunks y provider usage.
"""
```

Use `postgresql.UUID(as_uuid=True)` for UUID columns and `postgresql.JSONB()` for JSON columns in the migration. Use `sa.text("now()")` for server timestamps and `sa.text("false")` for Postgres boolean defaults. Keep SQLite compatibility in models through `JSONWithJSONB`.

- [ ] **Step 5: Run model tests**

Run:

```powershell
uv run pytest tests/unit/db/models/test_chat_audit_models.py -q
```

Expected: PASS.

- [ ] **Step 6: Run focused static checks**

Run:

```powershell
uv run ruff check src/adaptive_rag/db/models tests/unit/db/models/test_chat_audit_models.py
uv run mypy src
```

Expected: both commands pass.

- [ ] **Step 7: Commit schema and models**

Run:

```powershell
git add alembic/versions/b7a3c9d4e5f6_m13_chat_audit_trail.py src/adaptive_rag/db/models tests/unit/db/models/test_chat_audit_models.py
git commit -m "feat: add chat audit schema"
```

---

### Task 2: Chat Audit Repositories

**Files:**

- Create: `src/adaptive_rag/db/repositories/chat_audit.py`
- Modify: `src/adaptive_rag/db/repositories/__init__.py`
- Test: `tests/unit/db/repositories/test_chat_audit_repository.py`

- [ ] **Step 1: Write failing repository tests**

Create `tests/unit/db/repositories/test_chat_audit_repository.py`:

```python
"""Tests para repositories M13 de audit trail de chat."""

from __future__ import annotations

from uuid import uuid4

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
    RetrievedChunk,
    RetrievalRun,
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
    tool_calls = repo.list_tool_calls(project_id=project.id, session_id=chat_session.id)
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

    assert repo.get_session(project_id=other_project.id, session_id=chat_session.id) is None
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
    assert repo.list_retrieved_chunks(
        project_id=other_project.id,
        retrieval_run_id=retrieval_run.id,
    ) == []


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


def test_provider_usage_repository_persists_provider_call_record() -> None:
    session = _make_session()
    project = _make_project(session)
    repo = ChatAuditRepository(session)
    usage_repo = ProviderUsageRepository(session)
    chat_session = repo.create_session(project_id=project.id)
    record = ProviderCallRecord(
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
    )

    usage = usage_repo.create_from_record(
        project_id=project.id,
        session_id=chat_session.id,
        job_id=None,
        eval_run_id=None,
        record=record,
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
```

- [ ] **Step 2: Run repository tests and verify they fail**

Run:

```powershell
uv run pytest tests/unit/db/repositories/test_chat_audit_repository.py -q
```

Expected: FAIL during import because `ChatAuditRepository` and `ProviderUsageRepository` do not exist.

- [ ] **Step 3: Implement repositories**

Create `src/adaptive_rag/db/repositories/chat_audit.py` with:

```python
"""Repositories para audit trail de chat M13."""

from __future__ import annotations

import builtins
from collections.abc import Mapping
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from adaptive_rag.db.models import (
    ChatMessage,
    ChatSession,
    Chunk,
    Document,
    DocumentVersion,
    ProviderUsage,
    RetrievedChunk,
    RetrievalRun,
    ToolCall,
)
from adaptive_rag.provider_usage import ProviderCallRecord


class ChatAuditRepository:
    """Acceso a audit trail de chat con aislamiento por proyecto."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def create_session(
        self,
        *,
        project_id: UUID,
        model_config_json: Mapping[str, Any] | None = None,
        prompt_version: str | None = None,
    ) -> ChatSession:
        chat_session = ChatSession(
            project_id=project_id,
            model_config_json=(
                dict(model_config_json) if model_config_json is not None else None
            ),
            prompt_version=prompt_version,
        )
        self._session.add(chat_session)
        self._session.flush()
        return chat_session

    def get_session(self, *, project_id: UUID, session_id: UUID) -> ChatSession | None:
        statement = select(ChatSession).where(
            ChatSession.project_id == project_id,
            ChatSession.id == session_id,
        )
        return self._session.scalars(statement).one_or_none()

    def add_message(
        self,
        *,
        project_id: UUID,
        session_id: UUID,
        role: str,
        content: str,
        metadata_json: Mapping[str, Any] | None = None,
    ) -> ChatMessage:
        self._require_session(project_id=project_id, session_id=session_id)
        message = ChatMessage(
            project_id=project_id,
            session_id=session_id,
            role=role,
            content=content,
            metadata_json=dict(metadata_json) if metadata_json is not None else None,
        )
        self._session.add(message)
        self._session.flush()
        return message

    def list_messages(
        self,
        *,
        project_id: UUID,
        session_id: UUID,
    ) -> builtins.list[ChatMessage]:
        statement = (
            select(ChatMessage)
            .where(
                ChatMessage.project_id == project_id,
                ChatMessage.session_id == session_id,
            )
            .order_by(ChatMessage.created_at, ChatMessage.id)
        )
        return builtins.list(self._session.scalars(statement))

    def succeed_session(self, *, project_id: UUID, session_id: UUID) -> ChatSession:
        chat_session = self._require_session(
            project_id=project_id,
            session_id=session_id,
        )
        chat_session.status = "succeeded"
        chat_session.error_message = None
        self._session.flush()
        return chat_session

    def fail_session(
        self,
        *,
        project_id: UUID,
        session_id: UUID,
        error_message: str,
    ) -> ChatSession:
        chat_session = self._require_session(
            project_id=project_id,
            session_id=session_id,
        )
        chat_session.status = "failed"
        chat_session.error_message = error_message
        self._session.flush()
        return chat_session

    def start_tool_call(
        self,
        *,
        project_id: UUID,
        session_id: UUID,
        tool_name: str,
        arguments_json: Mapping[str, Any] | None = None,
    ) -> ToolCall:
        self._require_session(project_id=project_id, session_id=session_id)
        tool_call = ToolCall(
            project_id=project_id,
            session_id=session_id,
            tool_name=tool_name,
            arguments_json=(
                dict(arguments_json) if arguments_json is not None else None
            ),
        )
        self._session.add(tool_call)
        self._session.flush()
        return tool_call

    def complete_tool_call(
        self,
        *,
        project_id: UUID,
        tool_call_id: UUID,
        result_summary_json: Mapping[str, Any] | None,
        latency_ms: int | None,
    ) -> ToolCall:
        tool_call = self._require_tool_call(
            project_id=project_id,
            tool_call_id=tool_call_id,
        )
        tool_call.status = "succeeded"
        tool_call.result_summary_json = (
            dict(result_summary_json) if result_summary_json is not None else None
        )
        tool_call.latency_ms = latency_ms
        tool_call.error_message = None
        self._session.flush()
        return tool_call

    def fail_tool_call(
        self,
        *,
        project_id: UUID,
        tool_call_id: UUID,
        error_message: str,
        latency_ms: int | None,
    ) -> ToolCall:
        tool_call = self._require_tool_call(
            project_id=project_id,
            tool_call_id=tool_call_id,
        )
        tool_call.status = "failed"
        tool_call.error_message = error_message
        tool_call.latency_ms = latency_ms
        self._session.flush()
        return tool_call

    def list_tool_calls(
        self,
        *,
        project_id: UUID,
        session_id: UUID,
    ) -> builtins.list[ToolCall]:
        statement = (
            select(ToolCall)
            .where(ToolCall.project_id == project_id, ToolCall.session_id == session_id)
            .order_by(ToolCall.created_at, ToolCall.id)
        )
        return builtins.list(self._session.scalars(statement))

    def create_retrieval_run(
        self,
        *,
        project_id: UUID,
        session_id: UUID,
        tool_call_id: UUID | None,
        query: str,
        strategy: str,
        top_k: int,
        used_rerank: bool,
        filters_json: Mapping[str, Any] | None = None,
        latency_ms: int | None = None,
    ) -> RetrievalRun:
        self._require_session(project_id=project_id, session_id=session_id)
        if tool_call_id is not None:
            self._require_tool_call(project_id=project_id, tool_call_id=tool_call_id)
        retrieval_run = RetrievalRun(
            project_id=project_id,
            session_id=session_id,
            tool_call_id=tool_call_id,
            query=query,
            strategy=strategy,
            top_k=top_k,
            used_rerank=used_rerank,
            filters_json=dict(filters_json) if filters_json is not None else None,
            latency_ms=latency_ms,
        )
        self._session.add(retrieval_run)
        self._session.flush()
        return retrieval_run

    def list_retrieval_runs(
        self,
        *,
        project_id: UUID,
        session_id: UUID,
    ) -> builtins.list[RetrievalRun]:
        statement = (
            select(RetrievalRun)
            .where(
                RetrievalRun.project_id == project_id,
                RetrievalRun.session_id == session_id,
            )
            .order_by(RetrievalRun.created_at, RetrievalRun.id)
        )
        return builtins.list(self._session.scalars(statement))

    def add_retrieved_chunk(
        self,
        *,
        project_id: UUID,
        retrieval_run_id: UUID,
        chunk_id: UUID,
        rank: int,
        citation_json: Mapping[str, Any],
        dense_score: float | None = None,
        lexical_score: float | None = None,
        rrf_score: float | None = None,
        rerank_score: float | None = None,
    ) -> RetrievedChunk:
        self._require_retrieval_run(
            project_id=project_id,
            retrieval_run_id=retrieval_run_id,
        )
        if not self._chunk_belongs_to_project(project_id=project_id, chunk_id=chunk_id):
            raise ValueError("chunk does not belong to project")
        retrieved_chunk = RetrievedChunk(
            project_id=project_id,
            retrieval_run_id=retrieval_run_id,
            chunk_id=chunk_id,
            rank=rank,
            dense_score=dense_score,
            lexical_score=lexical_score,
            rrf_score=rrf_score,
            rerank_score=rerank_score,
            citation_json=dict(citation_json),
        )
        self._session.add(retrieved_chunk)
        self._session.flush()
        return retrieved_chunk

    def list_retrieved_chunks(
        self,
        *,
        project_id: UUID,
        retrieval_run_id: UUID,
    ) -> builtins.list[RetrievedChunk]:
        statement = (
            select(RetrievedChunk)
            .where(
                RetrievedChunk.project_id == project_id,
                RetrievedChunk.retrieval_run_id == retrieval_run_id,
            )
            .order_by(RetrievedChunk.rank)
        )
        return builtins.list(self._session.scalars(statement))

    def _require_session(self, *, project_id: UUID, session_id: UUID) -> ChatSession:
        chat_session = self.get_session(project_id=project_id, session_id=session_id)
        if chat_session is None:
            raise ValueError("chat session does not belong to project")
        return chat_session

    def _require_tool_call(self, *, project_id: UUID, tool_call_id: UUID) -> ToolCall:
        statement = select(ToolCall).where(
            ToolCall.project_id == project_id,
            ToolCall.id == tool_call_id,
        )
        tool_call = self._session.scalars(statement).one_or_none()
        if tool_call is None:
            raise ValueError("tool call does not belong to project")
        return tool_call

    def _require_retrieval_run(
        self,
        *,
        project_id: UUID,
        retrieval_run_id: UUID,
    ) -> RetrievalRun:
        statement = select(RetrievalRun).where(
            RetrievalRun.project_id == project_id,
            RetrievalRun.id == retrieval_run_id,
        )
        retrieval_run = self._session.scalars(statement).one_or_none()
        if retrieval_run is None:
            raise ValueError("retrieval run does not belong to project")
        return retrieval_run

    def _chunk_belongs_to_project(self, *, project_id: UUID, chunk_id: UUID) -> bool:
        statement = (
            select(Chunk.id)
            .join(DocumentVersion, Chunk.document_version_id == DocumentVersion.id)
            .join(Document, DocumentVersion.document_id == Document.id)
            .where(Chunk.id == chunk_id, Document.project_id == project_id)
        )
        return self._session.scalar(statement) is not None


class ProviderUsageRepository:
    """Persistencia durable de records provider sin secretos."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def create_from_record(
        self,
        *,
        project_id: UUID,
        session_id: UUID | None,
        job_id: UUID | None,
        eval_run_id: UUID | None,
        record: ProviderCallRecord,
    ) -> ProviderUsage:
        usage = ProviderUsage(
            project_id=project_id,
            session_id=session_id,
            job_id=job_id,
            eval_run_id=eval_run_id,
            operation=record.operation,
            provider=record.provider,
            model=record.model,
            provider_request_id=record.request_id,
            input_tokens=record.usage.input_tokens,
            output_tokens=record.usage.output_tokens,
            total_tokens=record.usage.total_tokens,
            input_count=record.usage.input_count,
            usage_source=record.usage_source,
            estimated_cost_usd=record.estimated_cost_usd,
            currency="USD",
            latency_ms=record.duration_ms,
            status=record.outcome,
            error_message=record.error_type,
        )
        self._session.add(usage)
        self._session.flush()
        return usage
```

Modify `src/adaptive_rag/db/repositories/__init__.py`:

```python
from adaptive_rag.db.repositories.chat_audit import (
    ChatAuditRepository,
    ProviderUsageRepository,
)
```

Add both names to `__all__`.

- [ ] **Step 4: Run repository tests**

Run:

```powershell
uv run pytest tests/unit/db/repositories/test_chat_audit_repository.py -q
```

Expected: PASS.

- [ ] **Step 5: Run model and repository tests together**

Run:

```powershell
uv run pytest tests/unit/db/models/test_chat_audit_models.py tests/unit/db/repositories/test_chat_audit_repository.py -q
```

Expected: PASS.

- [ ] **Step 6: Run focused static checks**

Run:

```powershell
uv run ruff check src/adaptive_rag/db/repositories tests/unit/db/repositories/test_chat_audit_repository.py
uv run mypy src
```

Expected: both commands pass.

- [ ] **Step 7: Commit repositories**

Run:

```powershell
git add src/adaptive_rag/db/repositories tests/unit/db/repositories/test_chat_audit_repository.py
git commit -m "feat: add chat audit repositories"
```

---

### Task 3: Chat Service Audit Wiring

**Files:**

- Create: `src/adaptive_rag/chat/audit.py`
- Modify: `src/adaptive_rag/chat/models.py`
- Modify: `src/adaptive_rag/chat/payloads.py`
- Modify: `src/adaptive_rag/chat/tools.py`
- Modify: `src/adaptive_rag/chat/service.py`
- Modify: `src/adaptive_rag/chat/__init__.py`
- Test: `tests/unit/chat/test_chat_audit_wiring.py`
- Test: `tests/unit/chat/test_chat_service.py`

- [ ] **Step 1: Write failing chat audit wiring tests**

Create `tests/unit/chat/test_chat_audit_wiring.py`:

```python
"""Tests de wiring audit trail en ChatService."""

from __future__ import annotations

from uuid import UUID, uuid4

import pytest

from adaptive_rag.chat import (
    ChatRequest,
    ChatRunnerOutput,
    ChatRunnerRequest,
    ChatService,
    ChatServiceError,
)
from adaptive_rag.chat.audit import InMemoryChatAuditWriter
from adaptive_rag.chat.payloads import serialize_chat_response
from adaptive_rag.chat.tools import ChatTools
from adaptive_rag.retrieval import (
    DenseRetrievalCitation,
    RetrievalSearchRequest,
    RetrievalSearchResult,
)


class RecordingRetrievalService:
    def __init__(self, results: list[RetrievalSearchResult]) -> None:
        self.results = results
        self.requests: list[RetrievalSearchRequest] = []

    def search(self, request: RetrievalSearchRequest) -> list[RetrievalSearchResult]:
        self.requests.append(request)
        return list(self.results)


class ToolCallingRunner:
    def __init__(self, *, query: str, cited_chunk_ids: tuple[UUID, ...]) -> None:
        self.query = query
        self.cited_chunk_ids = cited_chunk_ids

    def run(
        self,
        request: ChatRunnerRequest,
        tools: ChatTools,
    ) -> ChatRunnerOutput:
        tools.retrieval.search(query=self.query, limit=request.retrieval_limit)
        return ChatRunnerOutput(
            answer="Alpha is backed by retrieved evidence.",
            cited_chunk_ids=self.cited_chunk_ids,
        )


class RaisingRunner:
    def run(
        self,
        request: ChatRunnerRequest,
        tools: ChatTools,
    ) -> ChatRunnerOutput:
        tools.retrieval.search(query=request.message, limit=request.retrieval_limit)
        raise ChatServiceError("runner failed")


def test_chat_service_records_successful_session_tool_and_messages() -> None:
    project_id = uuid4()
    chunk_id = uuid4()
    audit = InMemoryChatAuditWriter(session_id=uuid4())
    service = ChatService(
        runner=ToolCallingRunner(query="alpha evidence", cited_chunk_ids=(chunk_id,)),
        retrieval_service=RecordingRetrievalService(
            [_retrieval_result(chunk_id=chunk_id, snippet="Alpha evidence")]
        ),
        audit_writer=audit,
    )

    response = service.respond(
        ChatRequest(
            project_id=project_id,
            message="What supports alpha?",
            retrieval_limit=1,
        )
    )

    assert response.session_id == audit.session_id
    assert audit.events[0] == {
        "event": "start_session",
        "project_id": str(project_id),
        "message": "What supports alpha?",
        "retrieval_limit": 1,
    }
    assert {"event": "message", "role": "user", "content": "What supports alpha?"} in audit.events
    assert {"event": "message", "role": "assistant", "content": response.answer} in audit.events
    assert audit.events[-1] == {"event": "succeed_session"}
    tool_events = [event for event in audit.events if event["event"] == "retrieval_tool"]
    assert tool_events == [
        {
            "event": "retrieval_tool",
            "query": "alpha evidence",
            "limit": 1,
            "result_count": 1,
            "chunk_ids": [str(chunk_id)],
        }
    ]
    assert serialize_chat_response(response)["session_id"] == str(audit.session_id)


def test_chat_service_records_failed_session_after_runner_error() -> None:
    project_id = uuid4()
    chunk_id = uuid4()
    audit = InMemoryChatAuditWriter(session_id=uuid4())
    service = ChatService(
        runner=RaisingRunner(),
        retrieval_service=RecordingRetrievalService(
            [_retrieval_result(chunk_id=chunk_id, snippet="Alpha evidence")]
        ),
        audit_writer=audit,
    )

    with pytest.raises(ChatServiceError, match="runner failed"):
        service.respond(ChatRequest(project_id=project_id, message="alpha"))

    assert audit.events[-1] == {
        "event": "fail_session",
        "error_message": "runner failed",
    }
    assert any(event["event"] == "retrieval_tool" for event in audit.events)


def test_invalid_request_does_not_start_audit_session() -> None:
    audit = InMemoryChatAuditWriter(session_id=uuid4())
    service = ChatService(
        runner=ToolCallingRunner(query="alpha", cited_chunk_ids=()),
        retrieval_service=RecordingRetrievalService([]),
        audit_writer=audit,
    )

    with pytest.raises(ChatServiceError, match="message must not be empty"):
        service.respond(ChatRequest(project_id=uuid4(), message=" "))

    assert audit.events == []


def _retrieval_result(*, chunk_id: UUID, snippet: str) -> RetrievalSearchResult:
    source_id = uuid4()
    document_id = uuid4()
    document_version_id = uuid4()
    citation = DenseRetrievalCitation(
        source_id=source_id,
        source_type="markdown",
        source_external_id="alpha.md",
        source_tags=("docs",),
        source_extra_metadata={"title": "Alpha"},
        document_id=document_id,
        document_stable_id="alpha-doc",
        document_version_id=document_version_id,
        document_version_number=1,
        chunk_id=chunk_id,
        char_start=0,
        char_end=len(snippet),
        snippet=snippet,
        section_metadata={"heading": "Alpha"},
    )
    return RetrievalSearchResult(
        chunk_id=chunk_id,
        distance=0.2,
        score=1 / 1.2,
        citation=citation,
        embedding_metadata={"provider": "fake"},
    )
```

- [ ] **Step 2: Run chat audit tests and verify they fail**

Run:

```powershell
uv run pytest tests/unit/chat/test_chat_audit_wiring.py -q
```

Expected: FAIL during import because `adaptive_rag.chat.audit` does not exist.

- [ ] **Step 3: Implement chat audit protocol and in-memory writer**

Create `src/adaptive_rag/chat/audit.py`:

```python
"""Audit writer abstractions for chat service."""

from __future__ import annotations

from dataclasses import dataclass, field
from time import monotonic
from typing import Any, Protocol
from uuid import UUID

from adaptive_rag.chat.models import ChatRequest
from adaptive_rag.db.repositories import ChatAuditRepository, ProviderUsageRepository
from adaptive_rag.provider_usage import ProviderCallRecord
from adaptive_rag.retrieval import RetrievalMetadataFilter
from adaptive_rag.retrieval.payloads import RetrievalResultPayload


class ChatAuditWriter(Protocol):
    """Sink used by ChatService and ChatRetrievalTool."""

    def start_session(self, *, request: ChatRequest, message: str) -> UUID | None:
        """Start a durable session after request validation."""

    def record_message(
        self,
        *,
        project_id: UUID,
        session_id: UUID | None,
        role: str,
        content: str,
        metadata_json: dict[str, Any] | None = None,
    ) -> None:
        """Record a chat message when a session exists."""

    def record_retrieval_tool(
        self,
        *,
        project_id: UUID,
        session_id: UUID | None,
        query: str,
        limit: int,
        metadata_filter: RetrievalMetadataFilter | None,
        latency_ms: int,
        results: tuple[RetrievalResultPayload, ...],
    ) -> None:
        """Record a retrieval tool call and its returned citations."""

    def succeed_session(
        self,
        *,
        project_id: UUID,
        session_id: UUID | None,
    ) -> None:
        """Mark a session as succeeded."""

    def fail_session(
        self,
        *,
        project_id: UUID,
        session_id: UUID | None,
        error_message: str,
    ) -> None:
        """Mark a session as failed."""

    def record_provider_usage(
        self,
        *,
        project_id: UUID,
        session_id: UUID | None,
        records: tuple[ProviderCallRecord, ...],
    ) -> None:
        """Persist provider usage records after session context is known."""


class NullChatAuditWriter:
    """No-op audit writer for tests and callers that do not persist audit trail."""

    def start_session(self, *, request: ChatRequest, message: str) -> UUID | None:
        return None

    def record_message(
        self,
        *,
        project_id: UUID,
        session_id: UUID | None,
        role: str,
        content: str,
        metadata_json: dict[str, Any] | None = None,
    ) -> None:
        return None

    def record_retrieval_tool(
        self,
        *,
        project_id: UUID,
        session_id: UUID | None,
        query: str,
        limit: int,
        metadata_filter: RetrievalMetadataFilter | None,
        latency_ms: int,
        results: tuple[RetrievalResultPayload, ...],
    ) -> None:
        return None

    def succeed_session(self, *, project_id: UUID, session_id: UUID | None) -> None:
        return None

    def fail_session(
        self,
        *,
        project_id: UUID,
        session_id: UUID | None,
        error_message: str,
    ) -> None:
        return None

    def record_provider_usage(
        self,
        *,
        project_id: UUID,
        session_id: UUID | None,
        records: tuple[ProviderCallRecord, ...],
    ) -> None:
        return None


@dataclass(slots=True)
class InMemoryChatAuditWriter:
    """Audit writer used by unit tests."""

    session_id: UUID
    events: list[dict[str, Any]] = field(default_factory=list)

    def start_session(self, *, request: ChatRequest, message: str) -> UUID:
        self.events.append(
            {
                "event": "start_session",
                "project_id": str(request.project_id),
                "message": message,
                "retrieval_limit": request.retrieval_limit,
            }
        )
        return self.session_id

    def record_message(
        self,
        *,
        project_id: UUID,
        session_id: UUID | None,
        role: str,
        content: str,
        metadata_json: dict[str, Any] | None = None,
    ) -> None:
        self.events.append({"event": "message", "role": role, "content": content})

    def record_retrieval_tool(
        self,
        *,
        project_id: UUID,
        session_id: UUID | None,
        query: str,
        limit: int,
        metadata_filter: RetrievalMetadataFilter | None,
        latency_ms: int,
        results: tuple[RetrievalResultPayload, ...],
    ) -> None:
        self.events.append(
            {
                "event": "retrieval_tool",
                "query": query,
                "limit": limit,
                "result_count": len(results),
                "chunk_ids": [result["chunk_id"] for result in results],
            }
        )

    def succeed_session(self, *, project_id: UUID, session_id: UUID | None) -> None:
        self.events.append({"event": "succeed_session"})

    def fail_session(
        self,
        *,
        project_id: UUID,
        session_id: UUID | None,
        error_message: str,
    ) -> None:
        self.events.append(
            {"event": "fail_session", "error_message": error_message}
        )

    def record_provider_usage(
        self,
        *,
        project_id: UUID,
        session_id: UUID | None,
        records: tuple[ProviderCallRecord, ...],
    ) -> None:
        self.events.append(
            {"event": "provider_usage", "record_count": len(records)}
        )


def elapsed_ms(start: float) -> int:
    return max(0, int((monotonic() - start) * 1000))
```

After Task 4, this same file will gain `SqlAlchemyChatAuditWriter`; keep the protocol stable now.

- [ ] **Step 4: Add session_id to chat response payloads**

Modify `src/adaptive_rag/chat/models.py`:

```python
@dataclass(frozen=True, slots=True)
class ChatResponse:
    """Respuesta conversacional serializable por futuras superficies API/CLI."""

    answer: str
    citations: tuple[RetrievalResultPayload, ...]
    tool_calls: tuple[ChatToolCall, ...]
    session_id: UUID | None = None
```

Modify `src/adaptive_rag/chat/payloads.py`:

```python
class ChatResponsePayload(TypedDict, total=False):
    answer: str
    citations: list[RetrievalResultPayload]
    tool_calls: list[ChatToolCallPayload]
    session_id: str
```

In `serialize_chat_response`, build the existing payload first and add `session_id` only when present:

```python
    if response.session_id is not None:
        payload["session_id"] = str(response.session_id)
    return payload
```

- [ ] **Step 5: Wire audit writer into ChatRetrievalTool**

Modify `src/adaptive_rag/chat/tools.py`:

```python
from time import monotonic

from adaptive_rag.chat.audit import ChatAuditWriter, NullChatAuditWriter, elapsed_ms
```

Add constructor parameters:

```python
        audit_writer: ChatAuditWriter | None = None,
        audit_session_id: UUID | None = None,
```

Store them:

```python
        self._audit_writer = audit_writer or NullChatAuditWriter()
        self._audit_session_id = audit_session_id
```

Wrap the retrieval call:

```python
        started_at = monotonic()
        try:
            results = self._retrieval_service.search(
                RetrievalSearchRequest(
                    project_id=self._project_id,
                    query=query,
                    limit=active_limit,
                    metadata_filter=active_filter,
                )
            )
        except RetrievalServiceError as exc:
            raise ChatServiceError(str(exc)) from exc

        latency_ms = elapsed_ms(started_at)
```

After `payloads` are built and `ChatToolCall` is appended, call:

```python
        self._audit_writer.record_retrieval_tool(
            project_id=self._project_id,
            session_id=self._audit_session_id,
            query=query,
            limit=active_limit,
            metadata_filter=active_filter,
            latency_ms=latency_ms,
            results=payloads,
        )
```

- [ ] **Step 6: Wire audit writer into ChatService**

Modify `src/adaptive_rag/chat/service.py` constructor:

```python
        audit_writer: ChatAuditWriter | None = None,
        provider_usage_records: Callable[[], tuple[ProviderCallRecord, ...]] | None = None,
```

Store:

```python
        self._audit_writer = audit_writer or NullChatAuditWriter()
        self._provider_usage_records = provider_usage_records or (lambda: ())
```

After validation, start audit:

```python
        session_id = self._audit_writer.start_session(
            request=request,
            message=message,
        )
        self._audit_writer.record_message(
            project_id=request.project_id,
            session_id=session_id,
            role="user",
            content=message,
            metadata_json={"retrieval_limit": request.retrieval_limit},
        )
```

Pass `audit_writer` and `session_id` to `ChatRetrievalTool`.

Wrap runner execution and citation resolution in `try/except ChatServiceError`:

```python
        try:
            output = self._runner.run(...)
            citations = _resolve_citations(...)
            response = ChatResponse(
                answer=output.answer,
                citations=citations,
                tool_calls=retrieval_tool.tool_calls,
                session_id=session_id,
            )
            self._audit_writer.record_message(
                project_id=request.project_id,
                session_id=session_id,
                role="assistant",
                content=response.answer,
            )
            self._audit_writer.record_provider_usage(
                project_id=request.project_id,
                session_id=session_id,
                records=self._provider_usage_records(),
            )
            self._audit_writer.succeed_session(
                project_id=request.project_id,
                session_id=session_id,
            )
            return response
        except ChatServiceError as exc:
            self._audit_writer.record_provider_usage(
                project_id=request.project_id,
                session_id=session_id,
                records=self._provider_usage_records(),
            )
            self._audit_writer.fail_session(
                project_id=request.project_id,
                session_id=session_id,
                error_message=str(exc),
            )
            raise
```

Catch only `ChatServiceError` in this task to preserve current error contract.

- [ ] **Step 7: Export audit types**

Modify `src/adaptive_rag/chat/__init__.py`:

```python
from adaptive_rag.chat.audit import (
    ChatAuditWriter,
    InMemoryChatAuditWriter,
    NullChatAuditWriter,
)
```

Add these names to `__all__`.

- [ ] **Step 8: Run chat unit tests**

Run:

```powershell
uv run pytest tests/unit/chat/test_chat_audit_wiring.py tests/unit/chat/test_chat_service.py -q
```

Expected: PASS.

- [ ] **Step 9: Run focused static checks**

Run:

```powershell
uv run ruff check src/adaptive_rag/chat tests/unit/chat
uv run mypy src
```

Expected: both commands pass.

- [ ] **Step 10: Commit chat service wiring**

Run:

```powershell
git add src/adaptive_rag/chat tests/unit/chat
git commit -m "feat: wire chat audit writer"
```

---

### Task 4: SQLAlchemy Audit Writer, API, and CLI Surface

**Files:**

- Modify: `src/adaptive_rag/chat/audit.py`
- Modify: `src/adaptive_rag/api/dependencies.py`
- Modify: `src/adaptive_rag/api/schemas/chat.py`
- Modify: `src/adaptive_rag/cli/chat.py`
- Test: `tests/integration/api/test_chat.py`
- Test: `tests/integration/cli/test_chat_cli.py`

- [ ] **Step 1: Add failing API integration assertions**

In `tests/integration/api/test_chat.py`, add new model imports:

```python
    ChatMessage,
    ChatSession,
    ProviderUsage,
    RetrievedChunk,
    RetrievalRun,
    ToolCall,
```

Include new tables in `_make_session()`:

```python
            ChatSession.__table__,
            ChatMessage.__table__,
            ToolCall.__table__,
            RetrievalRun.__table__,
            RetrievedChunk.__table__,
            ProviderUsage.__table__,
```

In `test_chat_endpoint_returns_answer_with_retrieval_citations`, after response assertions:

```python
    session_id = UUID(data["session_id"])
    chat_session = session.get(ChatSession, session_id)
    assert chat_session is not None
    assert chat_session.project_id == project.id
    assert chat_session.status == "succeeded"
    messages = session.query(ChatMessage).filter_by(session_id=session_id).all()
    assert [message.role for message in messages] == ["user", "assistant"]
    tool_calls = session.query(ToolCall).filter_by(session_id=session_id).all()
    assert len(tool_calls) == 1
    assert tool_calls[0].tool_name == "retrieval.search"
    retrieval_runs = session.query(RetrievalRun).filter_by(session_id=session_id).all()
    assert len(retrieval_runs) == 1
    retrieved_chunks = (
        session.query(RetrievedChunk)
        .filter_by(retrieval_run_id=retrieval_runs[0].id)
        .order_by(RetrievedChunk.rank)
        .all()
    )
    assert [item.chunk_id for item in retrieved_chunks] == [near.id, far.id]
```

- [ ] **Step 2: Add failing CLI integration assertions**

In `tests/integration/cli/test_chat_cli.py`, add the same model imports and `_make_session()` tables as API tests. In `test_chat_ask_command_outputs_api_compatible_json`, after JSON assertions:

```python
    session_id = UUID(data["session_id"])
    chat_session = session.get(ChatSession, session_id)
    assert chat_session is not None
    assert chat_session.status == "succeeded"
    assert session.query(ChatMessage).filter_by(session_id=session_id).count() == 2
    assert session.query(ToolCall).filter_by(session_id=session_id).count() == 1
    retrieval_run = session.query(RetrievalRun).filter_by(session_id=session_id).one()
    retrieved_chunks = (
        session.query(RetrievedChunk)
        .filter_by(retrieval_run_id=retrieval_run.id)
        .order_by(RetrievedChunk.rank)
        .all()
    )
    assert [item.chunk_id for item in retrieved_chunks] == [near.id, far.id]
```

- [ ] **Step 3: Run API/CLI tests and verify they fail**

Run:

```powershell
uv run pytest tests/integration/api/test_chat.py tests/integration/cli/test_chat_cli.py -q
```

Expected: FAIL because API/CLI responses do not include `session_id` and no audit writer is injected.

- [ ] **Step 4: Implement SQLAlchemyChatAuditWriter**

Append to `src/adaptive_rag/chat/audit.py`:

```python
class SqlAlchemyChatAuditWriter:
    """Persists chat audit events using repositories."""

    def __init__(
        self,
        *,
        chat_audit_repository: ChatAuditRepository,
        provider_usage_repository: ProviderUsageRepository,
    ) -> None:
        self._chat_repo = chat_audit_repository
        self._usage_repo = provider_usage_repository

    def start_session(self, *, request: ChatRequest, message: str) -> UUID:
        chat_session = self._chat_repo.create_session(project_id=request.project_id)
        return chat_session.id

    def record_message(
        self,
        *,
        project_id: UUID,
        session_id: UUID | None,
        role: str,
        content: str,
        metadata_json: dict[str, Any] | None = None,
    ) -> None:
        if session_id is None:
            return
        self._chat_repo.add_message(
            project_id=project_id,
            session_id=session_id,
            role=role,
            content=content,
            metadata_json=metadata_json,
        )

    def record_retrieval_tool(
        self,
        *,
        project_id: UUID,
        session_id: UUID | None,
        query: str,
        limit: int,
        metadata_filter: RetrievalMetadataFilter | None,
        latency_ms: int,
        results: tuple[RetrievalResultPayload, ...],
    ) -> None:
        if session_id is None:
            return
        tool_call = self._chat_repo.start_tool_call(
            project_id=project_id,
            session_id=session_id,
            tool_name="retrieval.search",
            arguments_json={
                "query": query,
                "limit": limit,
                "metadata_filter": serialize_metadata_filter(metadata_filter),
            },
        )
        self._chat_repo.complete_tool_call(
            project_id=project_id,
            tool_call_id=tool_call.id,
            result_summary_json={"result_count": len(results)},
            latency_ms=latency_ms,
        )
        retrieval_run = self._chat_repo.create_retrieval_run(
            project_id=project_id,
            session_id=session_id,
            tool_call_id=tool_call.id,
            query=query,
            strategy="dense",
            top_k=limit,
            used_rerank=any("rerank_metadata" in result for result in results),
            filters_json=serialize_metadata_filter(metadata_filter),
            latency_ms=latency_ms,
        )
        for rank, result in enumerate(results, start=1):
            self._chat_repo.add_retrieved_chunk(
                project_id=project_id,
                retrieval_run_id=retrieval_run.id,
                chunk_id=UUID(result["chunk_id"]),
                rank=rank,
                dense_score=result["score"],
                rerank_score=_rerank_score(result),
                citation_json=result["citation"],
            )

    def succeed_session(self, *, project_id: UUID, session_id: UUID | None) -> None:
        if session_id is not None:
            self._chat_repo.succeed_session(
                project_id=project_id,
                session_id=session_id,
            )

    def fail_session(
        self,
        *,
        project_id: UUID,
        session_id: UUID | None,
        error_message: str,
    ) -> None:
        if session_id is not None:
            self._chat_repo.fail_session(
                project_id=project_id,
                session_id=session_id,
                error_message=error_message,
            )

    def record_provider_usage(
        self,
        *,
        project_id: UUID,
        session_id: UUID | None,
        records: tuple[ProviderCallRecord, ...],
    ) -> None:
        for record in records:
            self._usage_repo.create_from_record(
                project_id=project_id,
                session_id=session_id,
                job_id=None,
                eval_run_id=None,
                record=record,
            )
```

Add helpers:

```python
def serialize_metadata_filter(
    metadata_filter: RetrievalMetadataFilter | None,
) -> dict[str, Any] | None:
    if metadata_filter is None:
        return None
    return {
        "source_id": str(metadata_filter.source_id)
        if metadata_filter.source_id is not None
        else None,
        "document_id": str(metadata_filter.document_id)
        if metadata_filter.document_id is not None
        else None,
        "source_type": metadata_filter.source_type,
        "tags": list(metadata_filter.tags),
        "source_created_at_from": metadata_filter.source_created_at_from.isoformat()
        if metadata_filter.source_created_at_from is not None
        else None,
        "source_created_at_to": metadata_filter.source_created_at_to.isoformat()
        if metadata_filter.source_created_at_to is not None
        else None,
        "document_created_at_from": metadata_filter.document_created_at_from.isoformat()
        if metadata_filter.document_created_at_from is not None
        else None,
        "document_created_at_to": metadata_filter.document_created_at_to.isoformat()
        if metadata_filter.document_created_at_to is not None
        else None,
    }


def _rerank_score(result: RetrievalResultPayload) -> float | None:
    metadata = result.get("rerank_metadata")
    if metadata is None:
        return None
    value = metadata.get("rerank_score")
    return value if isinstance(value, float) else None
```

Export `SqlAlchemyChatAuditWriter` from `src/adaptive_rag/chat/__init__.py`.

- [ ] **Step 5: Inject audit writer in FastAPI dependencies**

Modify `src/adaptive_rag/api/dependencies.py`:

```python
from adaptive_rag.chat import SqlAlchemyChatAuditWriter
from adaptive_rag.db.repositories import ChatAuditRepository, ProviderUsageRepository
from adaptive_rag.provider_usage import InMemoryProviderUsageTracker
```

Add:

```python
def get_provider_usage_tracker() -> InMemoryProviderUsageTracker:
    return InMemoryProviderUsageTracker()


def get_chat_audit_writer(
    session: Annotated[Session, Depends(get_session)],
) -> SqlAlchemyChatAuditWriter:
    return SqlAlchemyChatAuditWriter(
        chat_audit_repository=ChatAuditRepository(session),
        provider_usage_repository=ProviderUsageRepository(session),
    )
```

Modify `get_chat_runner` to accept the usage tracker:

```python
def get_chat_runner(
    usage_tracker: Annotated[
        InMemoryProviderUsageTracker,
        Depends(get_provider_usage_tracker),
    ],
) -> ChatRunner:
    return get_runtime_chat_runner(usage_tracker=usage_tracker)
```

Modify `get_chat_service` to accept and pass audit writer and tracker:

```python
    audit_writer: Annotated[
        SqlAlchemyChatAuditWriter,
        Depends(get_chat_audit_writer),
    ],
    usage_tracker: Annotated[
        InMemoryProviderUsageTracker,
        Depends(get_provider_usage_tracker),
    ],
) -> ChatService:
    return ChatService(
        runner=runner,
        retrieval_service=retrieval_service,
        audit_writer=audit_writer,
        provider_usage_records=lambda: usage_tracker.records,
    )
```

- [ ] **Step 6: Expose optional session_id in HTTP schema**

Modify `src/adaptive_rag/api/schemas/chat.py`:

```python
class ChatResponseBody(BaseModel):
    answer: str
    citations: list[RetrievalResultResponse]
    tool_calls: list[ChatToolCallResponse]
    session_id: UUID | None = None
```

No request schema changes.

- [ ] **Step 7: Inject audit writer in CLI**

Modify `src/adaptive_rag/cli/chat.py` imports:

```python
from adaptive_rag.chat import ChatRequest, ChatService, ChatServiceError, SqlAlchemyChatAuditWriter
from adaptive_rag.db.repositories import ChatAuditRepository, ProviderUsageRepository
from adaptive_rag.provider_usage import InMemoryProviderUsageTracker
```

Inside `with session_scope() as session:` create:

```python
        usage_tracker = InMemoryProviderUsageTracker()
        audit_writer = SqlAlchemyChatAuditWriter(
            chat_audit_repository=ChatAuditRepository(session),
            provider_usage_repository=ProviderUsageRepository(session),
        )
```

Pass to `ChatService`:

```python
            audit_writer=audit_writer,
            provider_usage_records=lambda: usage_tracker.records,
```

If `get_cli_chat_runner()` cannot accept the tracker yet, keep fake/local CLI behavior unchanged in this task and finish live usage tracker plumbing in Task 5.

- [ ] **Step 8: Run API/CLI integration tests**

Run:

```powershell
uv run pytest tests/integration/api/test_chat.py tests/integration/cli/test_chat_cli.py -q
```

Expected: PASS.

- [ ] **Step 9: Run focused static checks**

Run:

```powershell
uv run ruff check src/adaptive_rag/chat src/adaptive_rag/api src/adaptive_rag/cli tests/integration/api/test_chat.py tests/integration/cli/test_chat_cli.py
uv run mypy src
```

Expected: both commands pass.

- [ ] **Step 10: Commit API/CLI audit surface**

Run:

```powershell
git add src/adaptive_rag/chat src/adaptive_rag/api src/adaptive_rag/cli tests/integration/api/test_chat.py tests/integration/cli/test_chat_cli.py
git commit -m "feat: persist chat audit trail from api and cli"
```

---

### Task 5: Provider Usage Linking

**Files:**

- Modify: `src/adaptive_rag/cli/dependencies.py`
- Modify: `src/adaptive_rag/cli/chat.py`
- Modify: `src/adaptive_rag/api/dependencies.py`
- Test: `tests/unit/db/repositories/test_chat_audit_repository.py`
- Test: `tests/integration/api/test_chat.py`
- Test: `tests/integration/cli/test_chat_cli.py`

- [ ] **Step 1: Add failing usage linking test**

In `tests/integration/api/test_chat.py`, add a runner that records usage through dependency override:

```python
from adaptive_rag.api.dependencies import get_provider_usage_tracker
from adaptive_rag.provider_usage import (
    InMemoryProviderUsageTracker,
    ProviderCallRecord,
    ProviderTokenUsage,
)
```

Add:

```python
class UsageRecordingChatRunner(ToolCallingChatRunner):
    def __init__(
        self,
        *,
        retrieval_query: str,
        tracker: InMemoryProviderUsageTracker,
    ) -> None:
        super().__init__(retrieval_query=retrieval_query)
        self.tracker = tracker

    def run(
        self,
        request: ChatRunnerRequest,
        tools: ChatTools,
    ) -> ChatRunnerOutput:
        output = super().run(request, tools)
        self.tracker.record(
            ProviderCallRecord(
                provider="qwen",
                model="qwen-plus",
                operation="chat",
                outcome="succeeded",
                duration_ms=10,
                usage=ProviderTokenUsage(
                    input_tokens=3,
                    output_tokens=4,
                    total_tokens=7,
                    input_count=1,
                ),
                usage_source="provider_reported",
                estimated_cost_usd=0.00001,
                request_id="req-chat",
            )
        )
        return output
```

Create a test that overrides `get_provider_usage_tracker`, executes chat, and asserts one `ProviderUsage` row with `session_id`:

```python
def test_chat_endpoint_persists_provider_usage_with_session_id() -> None:
    session = _make_session()
    project = _create_project(session)
    _source, _document, _version, _chunk = _create_embedded_chunk(
        session,
        project=project,
        external_id="near.md",
        tags=("docs",),
        stable_id="near-doc",
        text="Alpha original evidence",
        snippet="Alpha original evidence",
        embedding=_vector(0.1),
    )
    session.commit()
    provider = StaticQueryEmbeddingProvider(_vector(0.0))
    tracker = InMemoryProviderUsageTracker()
    runner = UsageRecordingChatRunner(
        retrieval_query="alpha evidence",
        tracker=tracker,
    )
    client = _client(session=session, provider=provider, runner=runner)
    client.app.dependency_overrides[get_provider_usage_tracker] = lambda: tracker

    response = client.post(
        f"/projects/{project.id}/chat",
        json={"message": "What supports alpha?", "retrieval_limit": 1},
    )

    assert response.status_code == 200
    session_id = UUID(response.json()["session_id"])
    usage = session.query(ProviderUsage).one()
    assert usage.project_id == project.id
    assert usage.session_id == session_id
    assert usage.provider == "qwen"
    assert usage.model == "qwen-plus"
    assert usage.operation == "chat"
    assert usage.status == "succeeded"
    assert usage.total_tokens == 7
```

- [ ] **Step 2: Run usage linking test and verify it fails**

Run:

```powershell
uv run pytest tests/integration/api/test_chat.py::test_chat_endpoint_persists_provider_usage_with_session_id -q
```

Expected: FAIL if FastAPI dependency caching or `ChatService` is not receiving the same tracker used by the runner.

- [ ] **Step 3: Ensure API dependency shares the same request-scoped tracker**

In `src/adaptive_rag/api/dependencies.py`, keep `get_provider_usage_tracker` as a dependency callable and ensure both `get_chat_runner` and `get_chat_service` depend on that exact callable. FastAPI will cache the returned `InMemoryProviderUsageTracker` per request.

If `get_runtime_chat_runner` already accepts `usage_tracker`, the code from Task 4 is enough. If the signature differs, inspect `src/adaptive_rag/provider_runtime.py` and pass the tracker using its actual parameter name.

- [ ] **Step 4: Allow CLI live runtime to share a tracker**

Modify `src/adaptive_rag/cli/dependencies.py`:

```python
def get_cli_chat_runner_with_usage(
    usage_tracker: InMemoryProviderUsageTracker,
) -> ChatRunner:
    return get_chat_runner(usage_tracker=usage_tracker)
```

Modify `src/adaptive_rag/cli/chat.py` to import `get_cli_chat_runner_with_usage` and use:

```python
        usage_tracker = InMemoryProviderUsageTracker()
        service = ChatService(
            runner=get_cli_chat_runner_with_usage(usage_tracker),
            retrieval_service=retrieval_service,
            audit_writer=audit_writer,
            provider_usage_records=lambda: usage_tracker.records,
        )
```

- [ ] **Step 5: Run usage and chat integration tests**

Run:

```powershell
uv run pytest tests/integration/api/test_chat.py tests/integration/cli/test_chat_cli.py -q
```

Expected: PASS.

- [ ] **Step 6: Run provider usage unit tests**

Run:

```powershell
uv run pytest tests/unit/test_provider_usage.py tests/unit/db/repositories/test_chat_audit_repository.py -q
```

Expected: PASS.

- [ ] **Step 7: Run focused static checks**

Run:

```powershell
uv run ruff check src/adaptive_rag/api src/adaptive_rag/cli src/adaptive_rag/provider_usage.py tests/integration/api/test_chat.py
uv run mypy src
```

Expected: both commands pass.

- [ ] **Step 8: Commit provider usage linking**

Run:

```powershell
git add src/adaptive_rag/api src/adaptive_rag/cli tests/integration/api/test_chat.py tests/integration/cli/test_chat_cli.py tests/unit/db/repositories/test_chat_audit_repository.py
git commit -m "feat: link provider usage to chat sessions"
```

---

### Task 6: OpenSpec Task Updates and Quality Gate

**Files:**

- Modify: `openspec/changes/m13-chat-audit-trail/tasks.md`
- Modify: `docs/progress.md`
- Modify: `docs/roadmap.md`

- [ ] **Step 1: Mark completed M13 implementation tasks**

In `openspec/changes/m13-chat-audit-trail/tasks.md`, mark:

```markdown
- [x] 3.1 Implementar `m13-audit-schema`.
- [x] 3.2 Implementar `m13-audit-repositories`.
- [x] 3.3 Implementar `m13-chat-service-audit-wiring`.
- [x] 3.4 Implementar `m13-api-cli-audit-surface`.
- [x] 3.5 Implementar `m13-provider-usage-linking`.
```

Keep `3.6` unchecked until the full gate below passes.

- [ ] **Step 2: Run full test suite**

Run:

```powershell
uv run pytest
```

Expected: all tests pass.

- [ ] **Step 3: Run lint and types**

Run:

```powershell
uv run ruff check .
uv run mypy src
```

Expected: both commands pass.

- [ ] **Step 4: Run OpenSpec validation**

Run:

```powershell
npx --yes @fission-ai/openspec validate m13-chat-audit-trail --strict
npx --yes @fission-ai/openspec validate --specs --strict
```

Expected: change is valid and all canonical specs pass.

- [ ] **Step 5: Run chat CLI smoke**

Run the existing integration smoke through tests:

```powershell
uv run pytest tests/integration/cli/test_chat_cli.py -q
```

Expected: PASS, including `session_id` and persisted audit rows.

- [ ] **Step 6: Check whitespace**

Run:

```powershell
git diff --check
```

Expected: no whitespace errors.

- [ ] **Step 7: Mark M13 quality gate task complete**

After all validation commands pass, mark:

```markdown
- [x] 3.6 Ejecutar `m13-quality-gate` y archivar el change cuando M13 quede
  cerrado.
```

Do not archive the OpenSpec change in this task unless the user asks to close the whole milestone after review. If archiving is requested, run:

```powershell
npx --yes @fission-ai/openspec archive m13-chat-audit-trail --yes
```

- [ ] **Step 8: Commit quality gate docs**

Run:

```powershell
git add openspec/changes/m13-chat-audit-trail/tasks.md docs/progress.md docs/roadmap.md
git commit -m "docs: update m13 audit trail progress"
```

---

## Self-Review

Spec coverage:

- Durable sessions/messages/tool calls/retrieval runs/retrieved chunks: Tasks 1-4.
- Project isolation and chunk project validation: Task 2.
- Provider usage linked to durable context: Tasks 1, 2, and 5.
- API/CLI compatibility with optional `session_id`: Tasks 3 and 4.
- Offline fake behavior without credentials: Tasks 3-5.
- Exclusions for streaming/history/dashboards/ranking: Scope Lock and no implementation tasks add those surfaces.

Placeholder scan:

- This plan contains no unfinished markers and no incomplete sections.

Type consistency:

- Model names exported from `adaptive_rag.db.models` match repository and tests.
- Repository names exported from `adaptive_rag.db.repositories` match tests and API/CLI wiring.
- `ChatResponse.session_id` is `UUID | None` and serializes to string only when present.
- `ProviderUsageRepository.create_from_record()` accepts `ProviderCallRecord`, matching `adaptive_rag.provider_usage`.

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-06-21-m13-chat-audit-trail.md`.

Two execution options:

1. **Subagent-Driven (recommended)** - dispatch a fresh subagent per task, review between tasks, fast iteration.
2. **Inline Execution** - execute tasks in this session using `superpowers:executing-plans`, batch execution with checkpoints.
