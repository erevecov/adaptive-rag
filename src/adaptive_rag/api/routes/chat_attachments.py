"""Rutas HTTP de chat attachments (upload/delete/get-content, design §3)."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile
from sqlalchemy.orm import Session

from adaptive_rag.api.dependencies import (
    get_current_user,
    get_session,
    get_workspace_access,
)
from adaptive_rag.api.schemas.chat_attachments import ChatAttachmentUploadResponse
from adaptive_rag.auth import CurrentPrincipal
from adaptive_rag.chat.attachments import (
    MAX_CHAT_ATTACHMENT_BYTES,
    ChatAttachmentError,
    extract_document_text,
    resolve_attachment_type,
)
from adaptive_rag.chat.errors import ChatErrorPayload
from adaptive_rag.db.models import ChatAttachment, Workspace
from adaptive_rag.db.repositories import ChatAttachmentRepository, ChatAuditRepository

router = APIRouter(
    prefix="/workspaces/{workspace_id}/chat/attachments",
    tags=["chat"],
)


@router.post("", status_code=201, response_model=ChatAttachmentUploadResponse)
async def upload_chat_attachment(
    workspace_id: UUID,
    session: Annotated[Session, Depends(get_session)],
    current: Annotated[CurrentPrincipal, Depends(get_current_user)],
    _access: Annotated[tuple[Workspace, str], Depends(get_workspace_access)],
    file: Annotated[UploadFile | str, File()],
    session_id: Annotated[UUID | None, Form()] = None,
) -> ChatAttachmentUploadResponse:
    # Un part multipart sin filename (o con filename="") llega como campo
    # plano str: se traduce al 422 disenado en vez del error generico.
    if isinstance(file, str):
        raise HTTPException(
            status_code=422,
            detail=_error_detail(
                "missing_filename", "Attachment is missing a filename."
            ),
        )
    filename = (file.filename or "").strip()
    if not filename:
        raise HTTPException(
            status_code=422,
            detail=_error_detail(
                "missing_filename", "Attachment is missing a filename."
            ),
        )
    try:
        kind, mime = resolve_attachment_type(
            filename=filename,
            content_type=file.content_type,
        )
    except ChatAttachmentError as exc:
        raise HTTPException(
            status_code=422,
            detail=exc.to_payload().as_dict(),
        ) from exc

    # Cap + 1: reject oversize without loading unbounded bodies into memory.
    content = await file.read(MAX_CHAT_ATTACHMENT_BYTES + 1)
    if len(content) > MAX_CHAT_ATTACHMENT_BYTES:
        raise HTTPException(
            status_code=422,
            detail=_error_detail(
                "attachment_too_large",
                "Attachment exceeds the "
                f"{MAX_CHAT_ATTACHMENT_BYTES // (1024 * 1024)} MB size limit.",
            ),
        )
    if not content:
        raise HTTPException(
            status_code=422,
            detail=_error_detail("empty_file", "Attachment file is empty."),
        )

    if session_id is not None:
        chat_session = ChatAuditRepository(session).get_session(
            workspace_id=workspace_id,
            session_id=session_id,
        )
        if chat_session is None:
            raise HTTPException(
                status_code=404,
                detail=_error_detail(
                    "session_not_found",
                    "Chat session not found in this workspace.",
                ),
            )

    extracted_text: str | None = None
    if kind == "document":
        try:
            extracted_text = extract_document_text(mime=mime, content=content)
        except ChatAttachmentError as exc:
            raise HTTPException(
                status_code=422,
                detail=exc.to_payload().as_dict(),
            ) from exc

    attachment = ChatAttachmentRepository(session).create(
        workspace_id=workspace_id,
        user_id=current.user_id,
        session_id=session_id,
        kind=kind,
        mime=mime,
        filename=filename,
        size_bytes=len(content),
        content=content,
        extracted_text=extracted_text,
    )
    session.commit()
    return ChatAttachmentUploadResponse.from_attachment(attachment)


@router.delete("/{attachment_id}", status_code=204)
def delete_chat_attachment(
    workspace_id: UUID,
    attachment_id: UUID,
    session: Annotated[Session, Depends(get_session)],
    current: Annotated[CurrentPrincipal, Depends(get_current_user)],
    _access: Annotated[tuple[Workspace, str], Depends(get_workspace_access)],
) -> Response:
    attachment = _get_scoped_attachment(
        ChatAttachmentRepository(session),
        attachment_id=attachment_id,
        workspace_id=workspace_id,
        user_id=current.user_id,
    )
    if attachment is None:
        raise HTTPException(
            status_code=404,
            detail=_error_detail("attachment_not_found", "Attachment not found."),
        )
    session.delete(attachment)
    session.commit()
    return Response(status_code=204)


@router.get("/{attachment_id}/content")
def get_chat_attachment_content(
    workspace_id: UUID,
    attachment_id: UUID,
    session: Annotated[Session, Depends(get_session)],
    current: Annotated[CurrentPrincipal, Depends(get_current_user)],
    _access: Annotated[tuple[Workspace, str], Depends(get_workspace_access)],
) -> Response:
    attachment = _get_scoped_attachment(
        ChatAttachmentRepository(session),
        attachment_id=attachment_id,
        workspace_id=workspace_id,
        user_id=current.user_id,
    )
    if attachment is None:
        raise HTTPException(
            status_code=404,
            detail=_error_detail("attachment_not_found", "Attachment not found."),
        )
    # Inline disposition so browsers can render images/PDF in a lightbox tab;
    # filename is ASCII-sanitized for Content-Disposition compatibility.
    safe_name = _safe_content_disposition_filename(attachment.filename)
    return Response(
        content=attachment.content,
        media_type=attachment.mime,
        headers={
            "Content-Disposition": f'inline; filename="{safe_name}"',
            "Cache-Control": "private, max-age=60",
        },
    )


def _safe_content_disposition_filename(filename: str) -> str:
    cleaned = "".join(
        char if char.isalnum() or char in {".", "-", "_", " "} else "_"
        for char in filename.strip()
    ).strip()
    return cleaned[:180] if cleaned else "attachment"


def _error_detail(code: str, message: str) -> dict[str, object]:
    return ChatErrorPayload(code=code, message=message, retryable=False).as_dict()


def _get_scoped_attachment(
    repo: ChatAttachmentRepository,
    *,
    attachment_id: UUID,
    workspace_id: UUID,
    user_id: UUID | None,
) -> ChatAttachment | None:
    """Owned scoping; bootstrap principal (user_id None) cae a workspace scope."""

    if user_id is None:
        return repo.get(attachment_id=attachment_id, workspace_id=workspace_id)
    return repo.get_owned(
        attachment_id=attachment_id,
        workspace_id=workspace_id,
        user_id=user_id,
    )
