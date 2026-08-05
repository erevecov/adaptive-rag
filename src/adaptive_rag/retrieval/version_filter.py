"""Shared SQL constraints for document-version selection during retrieval."""

from __future__ import annotations

from sqlalchemy import ColumnElement, func, select
from sqlalchemy.orm import aliased

from adaptive_rag.db.models import DocumentVersion


def latest_document_version_clause() -> ColumnElement[bool]:
    """True when ``DocumentVersion`` is the highest ``version_number`` for its document.

    Superseded versions remain stored (and may still anchor historical citations),
    but search candidates must not surface them.
    """
    version_alias = aliased(DocumentVersion)
    max_version = (
        select(func.max(version_alias.version_number))
        .where(version_alias.document_id == DocumentVersion.document_id)
        .scalar_subquery()
    )
    return DocumentVersion.version_number == max_version
