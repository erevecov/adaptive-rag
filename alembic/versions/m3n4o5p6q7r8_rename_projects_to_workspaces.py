"""Rename product concept "projects" -> "workspaces" across the schema.

Revision ID: m3n4o5p6q7r8
Revises: l2m3n4o5p6q7
Create Date: 2026-08-10

Rename del concepto de dominio "proyecto" a "workspace":

- ``projects`` -> ``workspaces``
- ``project_memberships`` -> ``workspace_memberships``
- ``project_runtime_slot_overrides`` -> ``workspace_runtime_slot_overrides``
- ``project_chat_models`` -> ``workspace_chat_models``
- ``project_chat_retrieval_settings`` -> ``workspace_chat_retrieval_settings``
- columnas ``project_id`` -> ``workspace_id`` en todas las tablas que
  referencian al workspace
- ``users.last_project_id`` -> ``users.last_workspace_id``
- indexes, unique constraints y check constraints renombrados a la
  nomenclatura ``*workspace*``.

Preserva el behavior: mismos FKs, ondelete, tenancy y memberships. El
target de produccion y dev es PostgreSQL.
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "m3n4o5p6q7r8"
down_revision: str | Sequence[str] | None = "l2m3n4o5p6q7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _column_tables() -> list[str]:
    """Tablas (sin rename de tabla) con columna `project_id` -> `workspace_id`."""
    return [
        "sources",
        "documents",
        "chat_sessions",
        "chat_messages",
        "chat_attachments",
        "tool_calls",
        "retrieval_runs",
        "retrieved_chunks",
        "provider_usage",
        "jobs",
        "job_events",
        "user_memories",
        "knowledge_proposals",
        "graph_projections",
        # Tablas cuyo nombre cambia a workspace_*: su columna de scope tambien.
        "workspace_memberships",
        "workspace_runtime_slot_overrides",
        "workspace_chat_models",
        "workspace_chat_retrieval_settings",
    ]


def _index_renames() -> list[tuple[str, str, str]]:
    """(tabla, nombre_antiguo, nombre_nuevo)."""
    return [
        ("sources", "ix_sources_project_id", "ix_sources_workspace_id"),
        ("documents", "ix_documents_project_id", "ix_documents_workspace_id"),
        ("jobs", "ix_jobs_project_id", "ix_jobs_workspace_id"),
        ("job_events", "ix_job_events_project_id", "ix_job_events_workspace_id"),
        (
            "graph_projections",
            "ix_graph_projections_project_id",
            "ix_graph_projections_workspace_id",
        ),
        ("sources", "ix_sources_project_type", "ix_sources_workspace_type"),
        (
            "sources",
            "ix_sources_project_created_at",
            "ix_sources_workspace_created_at",
        ),
        (
            "chat_sessions",
            "ix_chat_sessions_project_created_at",
            "ix_chat_sessions_workspace_created_at",
        ),
        (
            "chat_sessions",
            "ix_chat_sessions_project_user_created_at",
            "ix_chat_sessions_workspace_user_created_at",
        ),
        (
            "chat_sessions",
            "ix_chat_sessions_project_status",
            "ix_chat_sessions_workspace_status",
        ),
        (
            "chat_sessions",
            "ix_chat_sessions_project_user_archived_created_at",
            "ix_chat_sessions_workspace_user_archived_created_at",
        ),
        (
            "chat_messages",
            "ix_chat_messages_project_session_created_at",
            "ix_chat_messages_workspace_session_created_at",
        ),
        (
            "tool_calls",
            "ix_tool_calls_project_session_created_at",
            "ix_tool_calls_workspace_session_created_at",
        ),
        (
            "retrieval_runs",
            "ix_retrieval_runs_project_session_created_at",
            "ix_retrieval_runs_workspace_session_created_at",
        ),
        (
            "retrieval_runs",
            "ix_retrieval_runs_project_strategy",
            "ix_retrieval_runs_workspace_strategy",
        ),
        (
            "retrieved_chunks",
            "ix_retrieved_chunks_project_retrieval_run_rank",
            "ix_retrieved_chunks_workspace_retrieval_run_rank",
        ),
        (
            "retrieved_chunks",
            "ix_retrieved_chunks_project_chunk",
            "ix_retrieved_chunks_workspace_chunk",
        ),
        (
            "provider_usage",
            "ix_provider_usage_project_session_created_at",
            "ix_provider_usage_workspace_session_created_at",
        ),
        (
            "provider_usage",
            "ix_provider_usage_project_operation_created_at",
            "ix_provider_usage_workspace_operation_created_at",
        ),
        (
            "provider_usage",
            "ix_provider_usage_project_job_created_at",
            "ix_provider_usage_workspace_job_created_at",
        ),
        (
            "provider_usage",
            "ix_provider_usage_project_eval_run_created_at",
            "ix_provider_usage_workspace_eval_run_created_at",
        ),
        (
            "jobs",
            "ix_jobs_project_status_run_after_priority",
            "ix_jobs_workspace_status_run_after_priority",
        ),
        (
            "jobs",
            "ix_jobs_project_locked_until",
            "ix_jobs_workspace_locked_until",
        ),
        ("jobs", "ix_jobs_project_created_at", "ix_jobs_workspace_created_at"),
        (
            "job_events",
            "ix_job_events_project_job_created_at",
            "ix_job_events_workspace_job_created_at",
        ),
        (
            "job_events",
            "ix_job_events_project_event_type",
            "ix_job_events_workspace_event_type",
        ),
        (
            "user_memories",
            "ix_user_memories_project_id",
            "ix_user_memories_workspace_id",
        ),
        (
            "user_memories",
            "ix_user_memories_user_project_status",
            "ix_user_memories_user_workspace_status",
        ),
        (
            "knowledge_proposals",
            "ix_knowledge_proposals_project_status_created_at",
            "ix_knowledge_proposals_workspace_status_created_at",
        ),
        (
            "knowledge_proposals",
            "ix_knowledge_proposals_project_submitter_created_at",
            "ix_knowledge_proposals_workspace_submitter_created_at",
        ),
        (
            "knowledge_proposals",
            "ix_knowledge_proposals_project_origin_session",
            "ix_knowledge_proposals_workspace_origin_session",
        ),
        (
            "graph_projections",
            "ix_graph_projections_project_status",
            "ix_graph_projections_workspace_status",
        ),
        ("chat_attachments", "ix_chat_attachments_project_user", "ix_chat_attachments_workspace_user"),
        ("projects", "ix_projects_deleted_at", "ix_workspaces_deleted_at"),
        (
            "workspace_chat_models",
            "ix_project_chat_models_project_default",
            "ix_workspace_chat_models_workspace_default",
        ),
        (
            "workspace_memberships",
            "ix_project_memberships_project_role",
            "ix_workspace_memberships_workspace_role",
        ),
        (
            "workspace_memberships",
            "ix_project_memberships_user_role",
            "ix_workspace_memberships_user_role",
        ),
        (
            "workspace_runtime_slot_overrides",
            "ix_project_runtime_slot_overrides_connection_id",
            "ix_workspace_runtime_slot_overrides_connection_id",
        ),
    ]


def _check_renames() -> list[tuple[str, str, str]]:
    """(tabla, nombre_antiguo, nombre_nuevo)."""
    return [
        ("workspaces", "projects_embedding_mode_check", "workspaces_embedding_mode_check"),
        (
            "workspace_memberships",
            "project_memberships_role_check",
            "workspace_memberships_role_check",
        ),
        (
            "workspace_runtime_slot_overrides",
            "project_runtime_slot_overrides_slot_check",
            "workspace_runtime_slot_overrides_slot_check",
        ),
        (
            "workspace_chat_retrieval_settings",
            "project_chat_retrieval_settings_retrieval_limit_check",
            "workspace_chat_retrieval_settings_retrieval_limit_check",
        ),
        (
            "workspace_chat_retrieval_settings",
            "project_chat_retrieval_settings_candidate_limit_check",
            "workspace_chat_retrieval_settings_candidate_limit_check",
        ),
        (
            "workspace_chat_retrieval_settings",
            "project_chat_retrieval_settings_rerank_window_check",
            "workspace_chat_retrieval_settings_rerank_window_check",
        ),
    ]


def _unique_renames() -> list[tuple[str, str, str]]:
    """(tabla, nombre_antiguo, nombre_nuevo)."""
    return [
        (
            "workspace_memberships",
            "uq_project_memberships_project_user",
            "uq_workspace_memberships_workspace_user",
        ),
        (
            "sources",
            "uq_sources_project_type_external_id",
            "uq_sources_workspace_type_external_id",
        ),
        (
            "graph_projections",
            "uq_graph_projections_project_backend",
            "uq_graph_projections_workspace_backend",
        ),
    ]


def _fk_renames() -> list[tuple[str, str, str]]:
    """(tabla, nombre_antiguo, nombre_nuevo)."""
    pairs = []
    # Estas 4 tablas renombraron (project_* -> workspace_*): su constraint FK
    # conserva el nombre antiguo del tipo <tabla_antigua>_project_id_fkey.
    renamed_tables = {
        "workspace_memberships",
        "workspace_runtime_slot_overrides",
        "workspace_chat_models",
        "workspace_chat_retrieval_settings",
    }
    for table in _column_tables():
        if table in renamed_tables:
            continue
        pairs.append(
            (
                table,
                f"{table}_project_id_fkey",
                f"{table}_workspace_id_fkey",
            )
        )
    pairs.append(
        (
            "users",
            "fk_users_last_project_id_projects",
            "fk_users_last_workspace_id_workspaces",
        )
    )
    # Tablas que renombraron: el constraint ya apunta a workspaces, solo
    # renombramos para seguir la nomenclatura.
    pairs.append(
        (
            "workspace_memberships",
            "project_memberships_project_id_fkey",
            "workspace_memberships_workspace_id_fkey",
        )
    )
    pairs.append(
        (
            "workspace_runtime_slot_overrides",
            "project_runtime_slot_overrides_project_id_fkey",
            "workspace_runtime_slot_overrides_workspace_id_fkey",
        )
    )
    pairs.append(
        (
            "workspace_chat_models",
            "project_chat_models_project_id_fkey",
            "workspace_chat_models_workspace_id_fkey",
        )
    )
    pairs.append(
        (
            "workspace_chat_retrieval_settings",
            "project_chat_retrieval_settings_project_id_fkey",
            "workspace_chat_retrieval_settings_workspace_id_fkey",
        )
    )
    # FKs sobre columnas que no son workspace_id pero que heredaron el nombre
    # de la tabla antigua (consistencia con la nomenclatura nueva).
    pairs.append(
        (
            "workspace_chat_models",
            "project_chat_models_connection_id_fkey",
            "workspace_chat_models_connection_id_fkey",
        )
    )
    pairs.append(
        (
            "workspace_memberships",
            "project_memberships_user_id_fkey",
            "workspace_memberships_user_id_fkey",
        )
    )
    pairs.append(
        (
            "workspace_runtime_slot_overrides",
            "project_runtime_slot_overrides_connection_id_fkey",
            "workspace_runtime_slot_overrides_connection_id_fkey",
        )
    )
    return pairs


def _rename_indexes(upgrading: bool) -> None:
    for _table, old_name, new_name in _index_renames():
        if upgrading:
            op.execute(f'ALTER INDEX IF EXISTS "{old_name}" RENAME TO "{new_name}"')
        else:
            op.execute(f'ALTER INDEX IF EXISTS "{new_name}" RENAME TO "{old_name}"')


def _rename_check_constraints(upgrading: bool) -> None:
    for table, old_name, new_name in _check_renames():
        if upgrading:
            op.execute(f'ALTER TABLE "{table}" RENAME CONSTRAINT "{old_name}" TO "{new_name}"')
        else:
            op.execute(f'ALTER TABLE "{table}" RENAME CONSTRAINT "{new_name}" TO "{old_name}"')


def _rename_unique_constraints(upgrading: bool) -> None:
    for table, old_name, new_name in _unique_renames():
        if upgrading:
            op.execute(f'ALTER TABLE "{table}" RENAME CONSTRAINT "{old_name}" TO "{new_name}"')
        else:
            op.execute(f'ALTER TABLE "{table}" RENAME CONSTRAINT "{new_name}" TO "{old_name}"')


def _rename_fks(upgrading: bool) -> None:
    for table, old_name, new_name in _fk_renames():
        if upgrading:
            op.execute(f'ALTER TABLE "{table}" RENAME CONSTRAINT "{old_name}" TO "{new_name}"')
        else:
            op.execute(f'ALTER TABLE "{table}" RENAME CONSTRAINT "{new_name}" TO "{old_name}"')


def _pkey_renames() -> list[tuple[str, str, str]]:
    """(tabla, nombre_antiguo, nombre_nuevo) de primary keys."""
    return [
        ("workspaces", "projects_pkey", "workspaces_pkey"),
        (
            "workspace_memberships",
            "project_memberships_pkey",
            "workspace_memberships_pkey",
        ),
        (
            "workspace_runtime_slot_overrides",
            "project_runtime_slot_overrides_pkey",
            "workspace_runtime_slot_overrides_pkey",
        ),
        (
            "workspace_chat_models",
            "project_chat_models_pkey",
            "workspace_chat_models_pkey",
        ),
        (
            "workspace_chat_retrieval_settings",
            "project_chat_retrieval_settings_pkey",
            "workspace_chat_retrieval_settings_pkey",
        ),
    ]


def _rename_pkeys(upgrading: bool) -> None:
    for table, old_name, new_name in _pkey_renames():
        if upgrading:
            op.execute(f'ALTER TABLE "{table}" RENAME CONSTRAINT "{old_name}" TO "{new_name}"')
        else:
            op.execute(f'ALTER TABLE "{table}" RENAME CONSTRAINT "{new_name}" TO "{old_name}"')


def upgrade() -> None:
    # 1) Tablas cuyo nombre cambia.
    op.rename_table("projects", "workspaces")
    op.rename_table("project_memberships", "workspace_memberships")
    op.rename_table(
        "project_runtime_slot_overrides", "workspace_runtime_slot_overrides"
    )
    op.rename_table("project_chat_models", "workspace_chat_models")
    op.rename_table(
        "project_chat_retrieval_settings", "workspace_chat_retrieval_settings"
    )

    # 2) Columnas project_id -> workspace_id.
    for table in _column_tables():
        with op.batch_alter_table(table) as batch_op:
            batch_op.alter_column("project_id", new_column_name="workspace_id")

    with op.batch_alter_table("users") as batch_op:
        batch_op.alter_column("last_project_id", new_column_name="last_workspace_id")

    # 3) Indexes, checks, uniques, pkeys y FKs.
    _rename_indexes(upgrading=True)
    _rename_check_constraints(upgrading=True)
    _rename_unique_constraints(upgrading=True)
    _rename_pkeys(upgrading=True)
    _rename_fks(upgrading=True)


def downgrade() -> None:
    _rename_fks(upgrading=False)
    _rename_pkeys(upgrading=False)
    _rename_unique_constraints(upgrading=False)
    _rename_check_constraints(upgrading=False)
    _rename_indexes(upgrading=False)

    for table in _column_tables():
        with op.batch_alter_table(table) as batch_op:
            batch_op.alter_column("workspace_id", new_column_name="project_id")

    with op.batch_alter_table("users") as batch_op:
        batch_op.alter_column("last_workspace_id", new_column_name="last_project_id")

    op.rename_table("workspace_chat_retrieval_settings", "project_chat_retrieval_settings")
    op.rename_table("workspace_chat_models", "project_chat_models")
    op.rename_table("workspace_runtime_slot_overrides", "project_runtime_slot_overrides")
    op.rename_table("workspace_memberships", "project_memberships")
    op.rename_table("workspaces", "projects")
