"""m2 domain schema

Revision ID: 6de20037eb1f
Revises:
Create Date: 2026-06-18 00:33:39.335539

Crea el schema de dominio de Adaptive RAG: projects, sources, documents,
document_versions, chunks y chunk_sparse_embeddings. Habilita la extension
vector de pgvector y define embedding denso vector(1024) sin HNSW (dense
exacto como baseline de correctness, decision D2 del design).
"""
from collections.abc import Sequence

import sqlalchemy as sa
from pgvector.sqlalchemy import Vector  # type: ignore[import-untyped]
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "6de20037eb1f"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

EMBEDDING_DIMENSIONS = 1024


def upgrade() -> None:
    # La extension vector es requerida por la columna chunks.embedding.
    # CREATE EXTENSION IF NOT EXISTS es idempotente y no falla si ya existe.
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "projects",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column(
            "embedding_mode",
            sa.String(),
            nullable=False,
            server_default="dense",
        ),
        sa.Column(
            "retrieval_contextualization_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column("budget_config_json", postgresql.JSONB(), nullable=True),
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
            "embedding_mode IN ('dense', 'dense_sparse')",
            name="projects_embedding_mode_check",
        ),
    )

    op.create_table(
        "sources",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "project_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("source_type", sa.String(), nullable=False),
        sa.Column("external_id", sa.String(), nullable=False),
        sa.Column("tags", postgresql.JSONB(), nullable=True),
        sa.Column("extra_metadata", postgresql.JSONB(), nullable=True),
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
        sa.UniqueConstraint(
            "project_id",
            "source_type",
            "external_id",
            name="uq_sources_project_type_external_id",
        ),
    )
    op.create_index("ix_sources_project_id", "sources", ["project_id"])
    op.create_index(
        "ix_sources_project_type",
        "sources",
        ["project_id", "source_type"],
    )
    op.create_index(
        "ix_sources_project_created_at",
        "sources",
        ["project_id", "created_at"],
    )
    op.create_index(
        "ix_sources_tags",
        "sources",
        ["tags"],
        postgresql_using="gin",
    )

    op.create_table(
        "documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "project_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "source_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("sources.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("stable_id", sa.String(), nullable=False),
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
        sa.UniqueConstraint(
            "source_id",
            "stable_id",
            name="uq_documents_source_stable_id",
        ),
    )
    op.create_index("ix_documents_project_id", "documents", ["project_id"])
    op.create_index("ix_documents_source_id", "documents", ["source_id"])

    op.create_table(
        "document_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "document_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("documents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("normalized_text", sa.Text(), nullable=False),
        sa.Column("content_hash", sa.String(), nullable=False),
        sa.Column("index_fingerprint", sa.String(), nullable=False),
        sa.Column("parser_metadata", postgresql.JSONB(), nullable=True),
        sa.Column("extraction_metadata", postgresql.JSONB(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "document_id",
            "version_number",
            name="uq_document_versions_document_version_number",
        ),
        sa.CheckConstraint(
            "version_number > 0",
            name="document_versions_version_number_positive_check",
        ),
    )
    op.create_index(
        "ix_document_versions_document_id", "document_versions", ["document_id"]
    )

    op.create_table(
        "chunks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "document_version_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("document_versions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("char_start", sa.Integer(), nullable=False),
        sa.Column("char_end", sa.Integer(), nullable=False),
        sa.Column("token_count", sa.Integer(), nullable=True),
        sa.Column(
            "prev_chunk_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("chunks.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "next_chunk_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("chunks.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("section_metadata", postgresql.JSONB(), nullable=True),
        sa.Column("chunker_metadata", postgresql.JSONB(), nullable=True),
        sa.Column("contextual_summary", sa.Text(), nullable=True),
        # Embedding denso baseline: vector(1024), sin HNSW.
        sa.Column("embedding", Vector(EMBEDDING_DIMENSIONS), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "document_version_id",
            "ordinal",
            name="uq_chunks_document_version_ordinal",
        ),
        sa.CheckConstraint(
            "ordinal >= 0",
            name="chunks_ordinal_non_negative_check",
        ),
        sa.CheckConstraint(
            "char_start >= 0",
            name="chunks_char_start_non_negative_check",
        ),
        sa.CheckConstraint(
            "char_end > char_start",
            name="chunks_char_range_check",
        ),
        sa.CheckConstraint(
            "token_count IS NULL OR token_count >= 0",
            name="chunks_token_count_non_negative_check",
        ),
    )
    op.create_index(
        "ix_chunks_document_version_id", "chunks", ["document_version_id"]
    )

    op.create_table(
        "chunk_sparse_embeddings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "chunk_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("chunks.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("sparse_indices", postgresql.JSONB(), nullable=False),
        sa.Column("sparse_values", postgresql.JSONB(), nullable=False),
        sa.Column("sparse_tokens", postgresql.JSONB(), nullable=True),
        sa.Column("sparse_size", sa.Integer(), nullable=False),
        sa.Column("input_hash", sa.String(), nullable=False),
        sa.Column("index_fingerprint", sa.String(), nullable=False),
        sa.Column("extra_metadata", postgresql.JSONB(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "chunk_id",
            "index_fingerprint",
            name="uq_chunk_sparse_embeddings_chunk_fingerprint",
        ),
        sa.CheckConstraint(
            "sparse_size >= 0",
            name="chunk_sparse_embeddings_sparse_size_non_negative_check",
        ),
    )
    op.create_index(
        "ix_chunk_sparse_embeddings_chunk_id",
        "chunk_sparse_embeddings",
        ["chunk_id"],
    )
    op.create_index(
        "ix_chunk_sparse_embeddings_sparse_indices",
        "chunk_sparse_embeddings",
        ["sparse_indices"],
        postgresql_using="gin",
    )


def downgrade() -> None:
    op.drop_index(
        "ix_chunk_sparse_embeddings_sparse_indices",
        table_name="chunk_sparse_embeddings",
    )
    op.drop_index(
        "ix_chunk_sparse_embeddings_chunk_id",
        table_name="chunk_sparse_embeddings",
    )
    op.drop_table("chunk_sparse_embeddings")

    op.drop_index("ix_chunks_document_version_id", table_name="chunks")
    op.drop_table("chunks")

    op.drop_index("ix_document_versions_document_id", table_name="document_versions")
    op.drop_table("document_versions")

    op.drop_index("ix_documents_source_id", table_name="documents")
    op.drop_index("ix_documents_project_id", table_name="documents")
    op.drop_table("documents")

    op.drop_index("ix_sources_tags", table_name="sources")
    op.drop_index("ix_sources_project_created_at", table_name="sources")
    op.drop_index("ix_sources_project_type", table_name="sources")
    op.drop_index("ix_sources_project_id", table_name="sources")
    op.drop_table("sources")

    op.drop_table("projects")

    # No eliminamos la extension vector: puede ser usada por otras bases
    # o migraciones posteriores, y DROP EXTENSION requiere privilegios.
