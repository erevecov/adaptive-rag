"""Constantes y helpers del lado upload para chat attachments (design §1/§3)."""

from __future__ import annotations

import base64
from collections.abc import Sequence
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.orm import Session

from adaptive_rag.chat.errors import ChatErrorPayload
from adaptive_rag.db.models.chat_attachment import ChatAttachment
from adaptive_rag.db.repositories.chat_attachments import ChatAttachmentRepository
from adaptive_rag.ingestion.parsers.registry import parser_for_content_type
from adaptive_rag.ingestion.types import IngestionPipelineError, normalize_text

MAX_CHAT_ATTACHMENT_BYTES = 10 * 1024 * 1024
MAX_ATTACHMENTS_PER_MESSAGE = 5
MAX_DOCUMENT_TEXT_CHARS = 8_000

ACCEPTED_IMAGE_MIMES = frozenset(
    {"image/png", "image/jpeg", "image/webp", "image/gif"}
)
ACCEPTED_DOCUMENT_MIMES = frozenset(
    {
        "text/plain",
        "text/markdown",
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    }
)

# Fallback por extension cuando el mime llega vacio u octet-stream (Safari).
EXTENSION_MIME_MAP = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".gif": "image/gif",
    ".md": "text/markdown",
    ".markdown": "text/markdown",
    ".txt": "text/plain",
    ".pdf": "application/pdf",
    ".docx": (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    ),
}

_TEXT_DOCUMENT_MIMES = frozenset({"text/plain", "text/markdown"})
_OCTET_STREAM_MIME = "application/octet-stream"

_UNSUPPORTED_TYPE_MESSAGE = (
    "Unsupported attachment type. Attach a png/jpeg/webp/gif image or a "
    "txt/md/pdf/docx document."
)


class ChatAttachmentError(ValueError):
    """Error de attachments con codigo machine-readable y mensaje operator-safe."""

    def __init__(self, message: str, *, code: str) -> None:
        super().__init__(message)
        self.message = message
        self.code = code

    def to_payload(self) -> ChatErrorPayload:
        return ChatErrorPayload(
            code=self.code,
            message=self.message,
            retryable=False,
        )


def resolve_attachment_type(
    *,
    filename: str,
    content_type: str | None,
) -> tuple[str, str]:
    """Resuelve (kind, mime) desde filename + content-type del upload."""

    mime = (content_type or "").split(";", 1)[0].strip().lower()
    if mime in ACCEPTED_IMAGE_MIMES:
        return "image", mime
    if mime in ACCEPTED_DOCUMENT_MIMES:
        return "document", mime
    if mime in ("", _OCTET_STREAM_MIME):
        extension = ""
        if "." in filename:
            extension = "." + filename.rsplit(".", 1)[1].strip().lower()
        mapped = EXTENSION_MIME_MAP.get(extension)
        if mapped is not None:
            kind = "image" if mapped in ACCEPTED_IMAGE_MIMES else "document"
            return kind, mapped
    raise ChatAttachmentError(
        _UNSUPPORTED_TYPE_MESSAGE,
        code="unsupported_attachment_type",
    )


def extract_document_text(*, mime: str, content: bytes) -> str:
    """Extrae texto del documento y lo trunca a MAX_DOCUMENT_TEXT_CHARS."""

    if mime in _TEXT_DOCUMENT_MIMES:
        text = normalize_text(content.decode("utf-8", errors="replace"))
    else:
        parser = parser_for_content_type(mime)
        if parser is None:
            raise ChatAttachmentError(
                _UNSUPPORTED_TYPE_MESSAGE,
                code="unsupported_attachment_type",
            )
        try:
            text = parser.parse(content).normalized_text
        except IngestionPipelineError as exc:
            raise ChatAttachmentError(
                "Could not extract text from the document. Use a text-based "
                "file (scanned PDFs without embedded text are not supported).",
                code="text_extraction_failed",
            ) from exc
    return text[:MAX_DOCUMENT_TEXT_CHARS]


@dataclass(frozen=True, slots=True)
class ChatAttachmentContext:
    """Adjunto resuelto y listo para inyectar en el turno del runner."""

    id: UUID
    kind: str
    filename: str
    mime: str
    image_data_url: str | None = None
    extracted_text: str | None = None


def load_chat_attachments(
    session_or_repo: Session | ChatAttachmentRepository,
    *,
    workspace_id: UUID,
    user_id: UUID | None,
    attachment_ids: Sequence[UUID],
) -> tuple[ChatAttachmentContext, ...]:
    """Resuelve adjuntos del usuario en el orden pedido (design §4).

    Cualquier id inexistente o ajeno a (workspace, user) -> invalid_attachment
    sin delatar cual falta. El principal bootstrap (user_id None) cae a
    workspace scope, como el helper de las rutas de upload.
    """

    repo = (
        session_or_repo
        if isinstance(session_or_repo, ChatAttachmentRepository)
        else ChatAttachmentRepository(session_or_repo)
    )
    rows: list[ChatAttachment | None] = []
    if user_id is None:
        rows = [
            repo.get(attachment_id=attachment_id, workspace_id=workspace_id)
            for attachment_id in attachment_ids
        ]
    else:
        owned = repo.list_owned_by_ids(
            workspace_id=workspace_id,
            user_id=user_id,
            attachment_ids=attachment_ids,
        )
        by_id = {row.id: row for row in owned}
        rows = [by_id.get(attachment_id) for attachment_id in attachment_ids]
    contexts: list[ChatAttachmentContext] = []
    for row in rows:
        if row is None:
            raise ChatAttachmentError(
                "One or more attachments are not available. "
                "Re-attach the files and try again.",
                code="invalid_attachment",
            )
        contexts.append(_attachment_context(row))
    return tuple(contexts)


def _attachment_context(attachment: ChatAttachment) -> ChatAttachmentContext:
    image_data_url: str | None = None
    if attachment.kind == "image":
        encoded = base64.b64encode(attachment.content).decode("ascii")
        image_data_url = f"data:{attachment.mime};base64,{encoded}"
    return ChatAttachmentContext(
        id=attachment.id,
        kind=attachment.kind,
        filename=attachment.filename,
        mime=attachment.mime,
        image_data_url=image_data_url,
        extracted_text=(
            attachment.extracted_text if attachment.kind == "document" else None
        ),
    )


def has_image_attachments(attachments: Sequence[ChatAttachmentContext]) -> bool:
    return any(
        attachment.kind == "image" and bool(attachment.image_data_url)
        for attachment in attachments
    )


def append_document_text_to_message(
    message: str,
    attachments: Sequence[ChatAttachmentContext],
) -> str:
    """Append extracted document text once, bounded per design §5."""

    documents = [
        attachment
        for attachment in attachments
        if attachment.kind == "document"
        and attachment.extracted_text
        and attachment.extracted_text.strip()
    ]
    if not documents:
        return message
    parts = [
        message,
        "=== USER-ATTACHED FILES (not retrieved from the knowledge base) ===",
    ]
    for document in documents:
        parts.append(f"[Attached: {document.filename}]\n{document.extracted_text}")
    return "\n\n".join(parts)


def attachment_metadata_refs(
    attachments: Sequence[ChatAttachmentContext],
) -> list[dict[str, str]]:
    """Serializable refs for user-message metadata (transcript re-render)."""

    return [
        {
            "id": str(attachment.id),
            "filename": attachment.filename,
            "kind": attachment.kind,
            "mime": attachment.mime,
        }
        for attachment in attachments
    ]
