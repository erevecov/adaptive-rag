"""m13 chat audit trail

Revision ID: b7a3c9d4e5f6
Revises: d3f6d8a1a9b2
Create Date: 2026-06-21 00:00:00.000000

Agrega tablas durables para auditar corridas de chat, tool calls, retrieval
runs, citations y usage/costo de providers.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b7a3c9d4e5f6"
down_revision: str | Sequence[str] | None = "d3f6d8a1a9b2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "chat_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "project_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("status", sa.String(), nullable=False, server_default="running"),
        sa.Column("model", sa.String(), nullable=True),
        sa.Column("prompt_config_json", postgresql.JSONB(), nullable=True),
        sa.Column("metadata_json", postgresql.JSONB(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status IN ('running', 'succeeded', 'failed')",
            name="chat_sessions_status_check",
        ),
    )
    op.create_index(
        "ix_chat_sessions_project_created_at",
        "chat_sessions",
        ["project_id", "created_at"],
    )
    op.create_index(
        "ix_chat_sessions_project_status",
        "chat_sessions",
        ["project_id", "status"],
    )

    op.create_table(
        "chat_messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "project_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "session_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("chat_sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("role", sa.String(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("metadata_json", postgresql.JSONB(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "role IN ('user', 'assistant')",
            name="chat_messages_role_check",
        ),
    )
    op.create_index(
        "ix_chat_messages_project_session_created_at",
        "chat_messages",
        ["project_id", "session_id", "created_at"],
    )

    op.create_table(
        "tool_calls",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "project_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "session_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("chat_sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("tool_name", sa.String(), nullable=False),
        sa.Column("arguments_json", postgresql.JSONB(), nullable=True),
        sa.Column("result_summary_json", postgresql.JSONB(), nullable=True),
        sa.Column("status", sa.String(), nullable=False, server_default="running"),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status IN ('running', 'succeeded', 'failed')",
            name="tool_calls_status_check",
        ),
        sa.CheckConstraint(
            "latency_ms IS NULL OR latency_ms >= 0",
            name="tool_calls_latency_ms_non_negative_check",
        ),
    )
    op.create_index(
        "ix_tool_calls_project_session_created_at",
        "tool_calls",
        ["project_id", "session_id", "created_at"],
    )

    op.create_table(
        "retrieval_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "project_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "session_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("chat_sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "tool_call_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tool_calls.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("query", sa.Text(), nullable=False),
        sa.Column("strategy", sa.String(), nullable=False),
        sa.Column("top_k", sa.Integer(), nullable=False),
        sa.Column(
            "used_rerank",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column("filters_json", postgresql.JSONB(), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "top_k > 0",
            name="retrieval_runs_top_k_positive_check",
        ),
        sa.CheckConstraint(
            "latency_ms IS NULL OR latency_ms >= 0",
            name="retrieval_runs_latency_ms_non_negative_check",
        ),
    )
    op.create_index(
        "ix_retrieval_runs_project_session_created_at",
        "retrieval_runs",
        ["project_id", "session_id", "created_at"],
    )
    op.create_index(
        "ix_retrieval_runs_project_strategy",
        "retrieval_runs",
        ["project_id", "strategy"],
    )

    op.create_table(
        "retrieved_chunks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "project_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "retrieval_run_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("retrieval_runs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "chunk_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("chunks.id"),
            nullable=False,
        ),
        sa.Column("rank", sa.Integer(), nullable=False),
        sa.Column("dense_score", sa.Float(), nullable=True),
        sa.Column("sparse_score", sa.Float(), nullable=True),
        sa.Column("rerank_score", sa.Float(), nullable=True),
        sa.Column("citation_json", postgresql.JSONB(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "retrieval_run_id",
            "rank",
            name="uq_retrieved_chunks_retrieval_run_rank",
        ),
        sa.CheckConstraint(
            "rank > 0",
            name="retrieved_chunks_rank_positive_check",
        ),
    )
    op.create_index(
        "ix_retrieved_chunks_project_retrieval_run_rank",
        "retrieved_chunks",
        ["project_id", "retrieval_run_id", "rank"],
    )
    op.create_index(
        "ix_retrieved_chunks_project_chunk",
        "retrieved_chunks",
        ["project_id", "chunk_id"],
    )

    op.create_table(
        "provider_usage",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "project_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "session_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("chat_sessions.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "job_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("jobs.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("eval_run_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("operation", sa.String(), nullable=False),
        sa.Column("provider", sa.String(), nullable=False),
        sa.Column("model", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("usage_source", sa.String(), nullable=False),
        sa.Column("input_tokens", sa.Integer(), nullable=True),
        sa.Column("output_tokens", sa.Integer(), nullable=True),
        sa.Column("total_tokens", sa.Integer(), nullable=True),
        sa.Column("input_count", sa.Integer(), nullable=True),
        sa.Column("estimated_cost_usd", sa.Float(), nullable=True),
        sa.Column("currency", sa.String(), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("request_id", sa.String(), nullable=True),
        sa.Column("error_type", sa.String(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "operation IN ('chat', 'contextualize', 'embedding', 'rerank', "
            "'eval_judge')",
            name="provider_usage_operation_check",
        ),
        sa.CheckConstraint(
            "status IN ('succeeded', 'failed', 'blocked')",
            name="provider_usage_status_check",
        ),
        sa.CheckConstraint(
            "usage_source IN ('provider_reported', 'estimated', 'unavailable')",
            name="provider_usage_source_check",
        ),
        sa.CheckConstraint(
            "input_tokens IS NULL OR input_tokens >= 0",
            name="provider_usage_input_tokens_non_negative_check",
        ),
        sa.CheckConstraint(
            "output_tokens IS NULL OR output_tokens >= 0",
            name="provider_usage_output_tokens_non_negative_check",
        ),
        sa.CheckConstraint(
            "total_tokens IS NULL OR total_tokens >= 0",
            name="provider_usage_total_tokens_non_negative_check",
        ),
        sa.CheckConstraint(
            "input_count IS NULL OR input_count >= 0",
            name="provider_usage_input_count_non_negative_check",
        ),
        sa.CheckConstraint(
            "latency_ms IS NULL OR latency_ms >= 0",
            name="provider_usage_latency_ms_non_negative_check",
        ),
        sa.CheckConstraint(
            "estimated_cost_usd IS NULL OR estimated_cost_usd >= 0",
            name="provider_usage_estimated_cost_usd_non_negative_check",
        ),
    )
    op.create_index(
        "ix_provider_usage_project_session_created_at",
        "provider_usage",
        ["project_id", "session_id", "created_at"],
    )
    op.create_index(
        "ix_provider_usage_project_operation_created_at",
        "provider_usage",
        ["project_id", "operation", "created_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_provider_usage_project_operation_created_at",
        table_name="provider_usage",
    )
    op.drop_index(
        "ix_provider_usage_project_session_created_at",
        table_name="provider_usage",
    )
    op.drop_table("provider_usage")

    op.drop_index("ix_retrieved_chunks_project_chunk", table_name="retrieved_chunks")
    op.drop_index(
        "ix_retrieved_chunks_project_retrieval_run_rank",
        table_name="retrieved_chunks",
    )
    op.drop_table("retrieved_chunks")

    op.drop_index("ix_retrieval_runs_project_strategy", table_name="retrieval_runs")
    op.drop_index(
        "ix_retrieval_runs_project_session_created_at",
        table_name="retrieval_runs",
    )
    op.drop_table("retrieval_runs")

    op.drop_index(
        "ix_tool_calls_project_session_created_at",
        table_name="tool_calls",
    )
    op.drop_table("tool_calls")

    op.drop_index(
        "ix_chat_messages_project_session_created_at",
        table_name="chat_messages",
    )
    op.drop_table("chat_messages")

    op.drop_index("ix_chat_sessions_project_status", table_name="chat_sessions")
    op.drop_index("ix_chat_sessions_project_created_at", table_name="chat_sessions")
    op.drop_table("chat_sessions")
