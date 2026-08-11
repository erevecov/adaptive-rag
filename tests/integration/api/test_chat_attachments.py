"""Tests de la superficie HTTP de chat attachments (upload/delete/content)."""

from __future__ import annotations

import base64
from collections.abc import Iterator
from pathlib import Path
from uuid import UUID, uuid4

from fastapi.testclient import TestClient
from httpx import Response
from sqlalchemy import URL, create_engine
from sqlalchemy.orm import Session, sessionmaker

from adaptive_rag.api.app import create_app
from adaptive_rag.api.dependencies import get_session
from adaptive_rag.auth import hash_access_token
from adaptive_rag.chat.attachments import (
    MAX_CHAT_ATTACHMENT_BYTES,
    MAX_DOCUMENT_TEXT_CHARS,
)
from adaptive_rag.db.base import Base
from adaptive_rag.db.models import (
    ChatAttachment,
    ChatSession,
    User,
    UserAccessToken,
    Workspace,
    WorkspaceMembership,
)
from adaptive_rag.db.repositories import (
    ChatAuditRepository,
    UserRepository,
    WorkspaceMembershipRepository,
    WorkspaceRepository,
)
from adaptive_rag.db.session import create_session_factory

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "m45"
SAMPLE_PDF = (FIXTURES / "sample.pdf").read_bytes()
EMPTY_TEXT_PDF = (FIXTURES / "empty_text.pdf").read_bytes()
SAMPLE_DOCX = (FIXTURES / "sample.docx").read_bytes()

# 1x1 transparent PNG.
PNG_BYTES = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk"
    "+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
)

DOCX_MIME = (
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
)


def _make_session_factory(tmp_path: Path) -> sessionmaker[Session]:
    engine = create_engine(
        URL.create(
            "sqlite+pysqlite",
            database=str(tmp_path / "chat-attachments-api.sqlite"),
        ),
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(
        engine,
        tables=[
            Workspace.__table__,
            User.__table__,
            UserAccessToken.__table__,
            WorkspaceMembership.__table__,
            ChatSession.__table__,
            ChatAttachment.__table__,
        ],
    )
    return create_session_factory(engine)


def _client(*, session: Session) -> TestClient:
    app = create_app()

    def override_session() -> Iterator[Session]:
        yield session

    app.dependency_overrides[get_session] = override_session
    return TestClient(app)


def _create_workspace(session: Session, name: str = "demo") -> Workspace:
    return WorkspaceRepository(session).create(name=name)


def _create_member(
    session: Session,
    *,
    workspace: Workspace,
    email: str,
    token: str,
    role: str = "viewer",
) -> User:
    repo = UserRepository(session)
    user = repo.create_user(
        email=email,
        display_name=email,
        system_role="user",
    )
    repo.upsert_access_token(
        user_id=user.id,
        token_hash=hash_access_token(token),
        label=f"{email} token",
    )
    WorkspaceMembershipRepository(session).upsert_membership(
        workspace_id=workspace.id,
        user_id=user.id,
        role=role,
    )
    return user


def _bearer(raw_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {raw_token}"}


def _upload(
    client: TestClient,
    *,
    workspace_id: UUID,
    token: str,
    filename: str,
    content: bytes,
    mime: str,
    session_id: UUID | None = None,
) -> Response:
    data = {"session_id": str(session_id)} if session_id is not None else None
    return client.post(
        f"/workspaces/{workspace_id}/chat/attachments",
        headers=_bearer(token),
        files={"file": (filename, content, mime)},
        data=data,
    )


def _error_code(response: Response) -> str:
    detail = response.json()["detail"]
    assert isinstance(detail, dict)
    return str(detail["code"])


def test_upload_png_image_returns_201_and_persists(tmp_path: Path) -> None:
    session_factory = _make_session_factory(tmp_path)
    session = session_factory()
    workspace = _create_workspace(session)
    user = _create_member(
        session, workspace=workspace, email="a@example.com", token="a-token"
    )
    session.commit()
    client = _client(session=session)

    response = _upload(
        client,
        workspace_id=workspace.id,
        token="a-token",
        filename="pixel.png",
        content=PNG_BYTES,
        mime="image/png",
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert set(body) == {"id", "kind", "filename", "mime", "size_bytes"}
    assert body["kind"] == "image"
    assert body["filename"] == "pixel.png"
    assert body["mime"] == "image/png"
    assert body["size_bytes"] == len(PNG_BYTES)

    fresh_session = session_factory()
    attachment = fresh_session.get(ChatAttachment, UUID(body["id"]))
    assert attachment is not None
    assert attachment.workspace_id == workspace.id
    assert attachment.user_id == user.id
    assert attachment.session_id is None
    assert attachment.content == PNG_BYTES
    assert attachment.extracted_text is None
    assert attachment.status == "ready"


def test_upload_pdf_document_extracts_text(tmp_path: Path) -> None:
    session_factory = _make_session_factory(tmp_path)
    session = session_factory()
    workspace = _create_workspace(session)
    _create_member(session, workspace=workspace, email="a@example.com", token="a-token")
    session.commit()
    client = _client(session=session)

    response = _upload(
        client,
        workspace_id=workspace.id,
        token="a-token",
        filename="sample.pdf",
        content=SAMPLE_PDF,
        mime="application/pdf",
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["kind"] == "document"
    assert body["mime"] == "application/pdf"

    fresh_session = session_factory()
    attachment = fresh_session.get(ChatAttachment, UUID(body["id"]))
    assert attachment is not None
    assert attachment.extracted_text is not None
    assert "ALPHA-PDF-442" in attachment.extracted_text


def test_upload_docx_document_extracts_text(tmp_path: Path) -> None:
    session_factory = _make_session_factory(tmp_path)
    session = session_factory()
    workspace = _create_workspace(session)
    _create_member(session, workspace=workspace, email="a@example.com", token="a-token")
    session.commit()
    client = _client(session=session)

    response = _upload(
        client,
        workspace_id=workspace.id,
        token="a-token",
        filename="sample.docx",
        content=SAMPLE_DOCX,
        mime=DOCX_MIME,
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["kind"] == "document"
    assert body["mime"] == DOCX_MIME

    fresh_session = session_factory()
    attachment = fresh_session.get(ChatAttachment, UUID(body["id"]))
    assert attachment is not None
    assert attachment.extracted_text is not None
    assert "ALPHA-DOCX-991" in attachment.extracted_text


def test_upload_txt_normalizes_and_markdown_via_extension_fallback(
    tmp_path: Path,
) -> None:
    session_factory = _make_session_factory(tmp_path)
    session = session_factory()
    workspace = _create_workspace(session)
    _create_member(session, workspace=workspace, email="a@example.com", token="a-token")
    session.commit()
    client = _client(session=session)

    txt = _upload(
        client,
        workspace_id=workspace.id,
        token="a-token",
        filename="notes.txt",
        content=b"  hello\r\nworld  ",
        mime="text/plain",
    )
    assert txt.status_code == 201, txt.text
    assert txt.json()["kind"] == "document"

    # Safari-style: empty/octet-stream mime falls back to the extension.
    md = _upload(
        client,
        workspace_id=workspace.id,
        token="a-token",
        filename="README.markdown",
        content=b"# Title",
        mime="application/octet-stream",
    )
    assert md.status_code == 201, md.text
    assert md.json()["kind"] == "document"
    assert md.json()["mime"] == "text/markdown"

    png = _upload(
        client,
        workspace_id=workspace.id,
        token="a-token",
        filename="photo.PNG",
        content=PNG_BYTES,
        mime="application/octet-stream",
    )
    assert png.status_code == 201, png.text
    assert png.json()["kind"] == "image"
    assert png.json()["mime"] == "image/png"

    fresh_session = session_factory()
    attachment = fresh_session.get(ChatAttachment, UUID(txt.json()["id"]))
    assert attachment is not None
    assert attachment.extracted_text == "hello\nworld"


def test_upload_document_text_is_truncated(tmp_path: Path) -> None:
    session_factory = _make_session_factory(tmp_path)
    session = session_factory()
    workspace = _create_workspace(session)
    _create_member(session, workspace=workspace, email="a@example.com", token="a-token")
    session.commit()
    client = _client(session=session)

    response = _upload(
        client,
        workspace_id=workspace.id,
        token="a-token",
        filename="long.txt",
        content=b"x" * (MAX_DOCUMENT_TEXT_CHARS + 1000),
        mime="text/plain",
    )

    assert response.status_code == 201, response.text
    fresh_session = session_factory()
    attachment = fresh_session.get(ChatAttachment, UUID(response.json()["id"]))
    assert attachment is not None
    assert attachment.extracted_text is not None
    assert len(attachment.extracted_text) == MAX_DOCUMENT_TEXT_CHARS


def test_upload_unsupported_type_returns_422(tmp_path: Path) -> None:
    session_factory = _make_session_factory(tmp_path)
    session = session_factory()
    workspace = _create_workspace(session)
    _create_member(session, workspace=workspace, email="a@example.com", token="a-token")
    session.commit()
    client = _client(session=session)

    zip_response = _upload(
        client,
        workspace_id=workspace.id,
        token="a-token",
        filename="archive.zip",
        content=b"PK\x03\x04payload",
        mime="application/zip",
    )
    assert zip_response.status_code == 422
    assert _error_code(zip_response) == "unsupported_attachment_type"

    unknown_extension = _upload(
        client,
        workspace_id=workspace.id,
        token="a-token",
        filename="blob.bin",
        content=b"payload",
        mime="application/octet-stream",
    )
    assert unknown_extension.status_code == 422
    assert _error_code(unknown_extension) == "unsupported_attachment_type"


def test_upload_too_large_returns_422(tmp_path: Path) -> None:
    session_factory = _make_session_factory(tmp_path)
    session = session_factory()
    workspace = _create_workspace(session)
    _create_member(session, workspace=workspace, email="a@example.com", token="a-token")
    session.commit()
    client = _client(session=session)

    response = _upload(
        client,
        workspace_id=workspace.id,
        token="a-token",
        filename="big.txt",
        content=b"a" * (MAX_CHAT_ATTACHMENT_BYTES + 1),
        mime="text/plain",
    )

    assert response.status_code == 422
    assert _error_code(response) == "attachment_too_large"


def test_upload_empty_file_returns_422(tmp_path: Path) -> None:
    session_factory = _make_session_factory(tmp_path)
    session = session_factory()
    workspace = _create_workspace(session)
    _create_member(session, workspace=workspace, email="a@example.com", token="a-token")
    session.commit()
    client = _client(session=session)

    response = _upload(
        client,
        workspace_id=workspace.id,
        token="a-token",
        filename="empty.txt",
        content=b"",
        mime="text/plain",
    )

    assert response.status_code == 422
    assert _error_code(response) == "empty_file"


def test_upload_missing_filename_returns_422(tmp_path: Path) -> None:
    session_factory = _make_session_factory(tmp_path)
    session = session_factory()
    workspace = _create_workspace(session)
    _create_member(session, workspace=workspace, email="a@example.com", token="a-token")
    session.commit()
    client = _client(session=session)

    response = _upload(
        client,
        workspace_id=workspace.id,
        token="a-token",
        filename="",
        content=b"payload",
        mime="text/plain",
    )

    assert response.status_code == 422
    assert _error_code(response) == "missing_filename"


def test_upload_pdf_without_embedded_text_returns_422(tmp_path: Path) -> None:
    session_factory = _make_session_factory(tmp_path)
    session = session_factory()
    workspace = _create_workspace(session)
    _create_member(session, workspace=workspace, email="a@example.com", token="a-token")
    session.commit()
    client = _client(session=session)

    response = _upload(
        client,
        workspace_id=workspace.id,
        token="a-token",
        filename="scanned.pdf",
        content=EMPTY_TEXT_PDF,
        mime="application/pdf",
    )

    assert response.status_code == 422
    assert _error_code(response) == "text_extraction_failed"


def test_upload_with_session_id_links_chat_session(tmp_path: Path) -> None:
    session_factory = _make_session_factory(tmp_path)
    session = session_factory()
    workspace = _create_workspace(session)
    user = _create_member(
        session, workspace=workspace, email="a@example.com", token="a-token"
    )
    chat_session = ChatAuditRepository(session).create_session(
        workspace_id=workspace.id,
        user_id=user.id,
    )
    session.commit()
    client = _client(session=session)

    response = _upload(
        client,
        workspace_id=workspace.id,
        token="a-token",
        filename="pixel.png",
        content=PNG_BYTES,
        mime="image/png",
        session_id=chat_session.id,
    )

    assert response.status_code == 201, response.text
    fresh_session = session_factory()
    attachment = fresh_session.get(ChatAttachment, UUID(response.json()["id"]))
    assert attachment is not None
    assert attachment.session_id == chat_session.id


def test_upload_with_foreign_or_missing_session_returns_404(tmp_path: Path) -> None:
    session_factory = _make_session_factory(tmp_path)
    session = session_factory()
    workspace = _create_workspace(session)
    other_workspace = _create_workspace(session, name="other")
    _create_member(session, workspace=workspace, email="a@example.com", token="a-token")
    foreign_session = ChatAuditRepository(session).create_session(
        workspace_id=other_workspace.id,
    )
    session.commit()
    client = _client(session=session)

    foreign = _upload(
        client,
        workspace_id=workspace.id,
        token="a-token",
        filename="pixel.png",
        content=PNG_BYTES,
        mime="image/png",
        session_id=foreign_session.id,
    )
    assert foreign.status_code == 404
    assert _error_code(foreign) == "session_not_found"

    missing = _upload(
        client,
        workspace_id=workspace.id,
        token="a-token",
        filename="pixel.png",
        content=PNG_BYTES,
        mime="image/png",
        session_id=uuid4(),
    )
    assert missing.status_code == 404
    assert _error_code(missing) == "session_not_found"


def test_get_content_roundtrip_returns_bytes_and_mime(tmp_path: Path) -> None:
    session_factory = _make_session_factory(tmp_path)
    session = session_factory()
    workspace = _create_workspace(session)
    _create_member(session, workspace=workspace, email="a@example.com", token="a-token")
    session.commit()
    client = _client(session=session)

    upload = _upload(
        client,
        workspace_id=workspace.id,
        token="a-token",
        filename="pixel.png",
        content=PNG_BYTES,
        mime="image/png",
    )
    assert upload.status_code == 201, upload.text
    attachment_id = upload.json()["id"]

    content = client.get(
        f"/workspaces/{workspace.id}/chat/attachments/{attachment_id}/content",
        headers=_bearer("a-token"),
    )

    assert content.status_code == 200
    assert content.content == PNG_BYTES
    assert content.headers["content-type"] == "image/png"


def test_other_user_cannot_read_or_delete_attachment(tmp_path: Path) -> None:
    session_factory = _make_session_factory(tmp_path)
    session = session_factory()
    workspace = _create_workspace(session)
    _create_member(session, workspace=workspace, email="a@example.com", token="a-token")
    _create_member(session, workspace=workspace, email="b@example.com", token="b-token")
    session.commit()
    client = _client(session=session)

    upload = _upload(
        client,
        workspace_id=workspace.id,
        token="a-token",
        filename="pixel.png",
        content=PNG_BYTES,
        mime="image/png",
    )
    assert upload.status_code == 201, upload.text
    attachment_id = upload.json()["id"]

    foreign_get = client.get(
        f"/workspaces/{workspace.id}/chat/attachments/{attachment_id}/content",
        headers=_bearer("b-token"),
    )
    assert foreign_get.status_code == 404
    assert _error_code(foreign_get) == "attachment_not_found"

    foreign_delete = client.delete(
        f"/workspaces/{workspace.id}/chat/attachments/{attachment_id}",
        headers=_bearer("b-token"),
    )
    assert foreign_delete.status_code == 404
    assert _error_code(foreign_delete) == "attachment_not_found"

    missing_get = client.get(
        f"/workspaces/{workspace.id}/chat/attachments/{uuid4()}/content",
        headers=_bearer("a-token"),
    )
    assert missing_get.status_code == 404
    assert _error_code(missing_get) == "attachment_not_found"

    # Still readable by the owner after the foreign attempts.
    owner_get = client.get(
        f"/workspaces/{workspace.id}/chat/attachments/{attachment_id}/content",
        headers=_bearer("a-token"),
    )
    assert owner_get.status_code == 200


def test_delete_then_get_returns_404(tmp_path: Path) -> None:
    session_factory = _make_session_factory(tmp_path)
    session = session_factory()
    workspace = _create_workspace(session)
    _create_member(session, workspace=workspace, email="a@example.com", token="a-token")
    session.commit()
    client = _client(session=session)

    upload = _upload(
        client,
        workspace_id=workspace.id,
        token="a-token",
        filename="pixel.png",
        content=PNG_BYTES,
        mime="image/png",
    )
    assert upload.status_code == 201, upload.text
    attachment_id = upload.json()["id"]

    deleted = client.delete(
        f"/workspaces/{workspace.id}/chat/attachments/{attachment_id}",
        headers=_bearer("a-token"),
    )
    assert deleted.status_code == 204
    assert deleted.content == b""

    fresh_session = session_factory()
    assert fresh_session.get(ChatAttachment, UUID(attachment_id)) is None

    get_after_delete = client.get(
        f"/workspaces/{workspace.id}/chat/attachments/{attachment_id}/content",
        headers=_bearer("a-token"),
    )
    assert get_after_delete.status_code == 404
    assert _error_code(get_after_delete) == "attachment_not_found"

    delete_again = client.delete(
        f"/workspaces/{workspace.id}/chat/attachments/{attachment_id}",
        headers=_bearer("a-token"),
    )
    assert delete_again.status_code == 404


def test_unauthenticated_requests_return_401(tmp_path: Path) -> None:
    session_factory = _make_session_factory(tmp_path)
    session = session_factory()
    workspace = _create_workspace(session)
    _create_member(session, workspace=workspace, email="a@example.com", token="a-token")
    session.commit()
    client = _client(session=session)

    upload = client.post(
        f"/workspaces/{workspace.id}/chat/attachments",
        files={"file": ("pixel.png", PNG_BYTES, "image/png")},
    )
    assert upload.status_code == 401

    get_content = client.get(
        f"/workspaces/{workspace.id}/chat/attachments/{uuid4()}/content",
    )
    assert get_content.status_code == 401

    delete = client.delete(
        f"/workspaces/{workspace.id}/chat/attachments/{uuid4()}",
    )
    assert delete.status_code == 401
