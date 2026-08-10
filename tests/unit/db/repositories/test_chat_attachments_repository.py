"""Tests para ChatAttachmentRepository (adjuntos de chat, design §2/§7)."""

from __future__ import annotations

from uuid import uuid4

from adaptive_rag.db.base import Base
from adaptive_rag.db.models import ChatAttachment, ChatSession, User, Workspace
from adaptive_rag.db.repositories import ChatAttachmentRepository, WorkspaceRepository
from adaptive_rag.db.session import create_engine_from_url, create_session_factory


def _make_session():
    engine = create_engine_from_url("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(
        engine,
        tables=[
            Workspace.__table__,
            User.__table__,
            ChatSession.__table__,
            ChatAttachment.__table__,
        ],
    )
    return create_session_factory(engine)()


def _make_workspace(session, name: str = "demo") -> Workspace:
    return WorkspaceRepository(session).create(name=name)


def _make_user(session, login: str) -> User:
    user = User(login=login, display_name=login)
    session.add(user)
    session.flush()
    return user


def _make_chat_session(session, *, workspace: Workspace, user: User) -> ChatSession:
    chat_session = ChatSession(workspace_id=workspace.id, user_id=user.id)
    session.add(chat_session)
    session.flush()
    return chat_session


def test_create_and_get_roundtrip_persists_all_fields() -> None:
    session = _make_session()
    workspace = _make_workspace(session)
    user = _make_user(session, "owner@example.com")
    chat_session = _make_chat_session(session, workspace=workspace, user=user)
    repo = ChatAttachmentRepository(session)

    attachment = repo.create(
        workspace_id=workspace.id,
        user_id=user.id,
        session_id=chat_session.id,
        kind="document",
        mime="text/plain",
        filename="notes.txt",
        size_bytes=5,
        content=b"hello",
        extracted_text="hello",
    )

    fetched = repo.get(attachment_id=attachment.id, workspace_id=workspace.id)

    assert fetched is not None
    assert fetched.id == attachment.id
    assert fetched.workspace_id == workspace.id
    assert fetched.user_id == user.id
    assert fetched.session_id == chat_session.id
    assert fetched.kind == "document"
    assert fetched.mime == "text/plain"
    assert fetched.filename == "notes.txt"
    assert fetched.size_bytes == 5
    assert fetched.content == b"hello"
    assert fetched.extracted_text == "hello"
    assert fetched.status == "ready"
    assert fetched.created_at is not None


def test_create_defaults_optional_fields() -> None:
    session = _make_session()
    workspace = _make_workspace(session)
    repo = ChatAttachmentRepository(session)

    attachment = repo.create(
        workspace_id=workspace.id,
        kind="image",
        mime="image/png",
        filename="pixel.png",
        size_bytes=4,
        content=b"\x89PNG",
    )

    fetched = repo.get(attachment_id=attachment.id, workspace_id=workspace.id)

    assert fetched is not None
    assert fetched.user_id is None
    assert fetched.session_id is None
    assert fetched.extracted_text is None
    assert fetched.status == "ready"


def test_get_is_scoped_to_workspace() -> None:
    session = _make_session()
    workspace = _make_workspace(session, "demo")
    other_workspace = _make_workspace(session, "other")
    repo = ChatAttachmentRepository(session)
    attachment = repo.create(
        workspace_id=workspace.id,
        kind="image",
        mime="image/png",
        filename="pixel.png",
        size_bytes=4,
        content=b"\x89PNG",
    )

    assert (
        repo.get(attachment_id=attachment.id, workspace_id=other_workspace.id) is None
    )
    assert repo.get(attachment_id=uuid4(), workspace_id=workspace.id) is None


def test_get_owned_is_scoped_to_user_and_workspace() -> None:
    session = _make_session()
    workspace = _make_workspace(session, "demo")
    other_workspace = _make_workspace(session, "other")
    owner = _make_user(session, "owner@example.com")
    other_user = _make_user(session, "other@example.com")
    repo = ChatAttachmentRepository(session)
    attachment = repo.create(
        workspace_id=workspace.id,
        user_id=owner.id,
        kind="image",
        mime="image/png",
        filename="pixel.png",
        size_bytes=4,
        content=b"\x89PNG",
    )

    owned = repo.get_owned(
        attachment_id=attachment.id,
        workspace_id=workspace.id,
        user_id=owner.id,
    )
    wrong_user = repo.get_owned(
        attachment_id=attachment.id,
        workspace_id=workspace.id,
        user_id=other_user.id,
    )
    wrong_workspace = repo.get_owned(
        attachment_id=attachment.id,
        workspace_id=other_workspace.id,
        user_id=owner.id,
    )

    assert owned is not None and owned.id == attachment.id
    assert wrong_user is None
    assert wrong_workspace is None


def test_list_owned_by_ids_returns_only_owned_attachments() -> None:
    session = _make_session()
    workspace = _make_workspace(session, "demo")
    other_workspace = _make_workspace(session, "other")
    owner = _make_user(session, "owner@example.com")
    other_user = _make_user(session, "other@example.com")
    repo = ChatAttachmentRepository(session)

    def _create(**overrides) -> ChatAttachment:
        values = {
            "workspace_id": workspace.id,
            "user_id": owner.id,
            "kind": "image",
            "mime": "image/png",
            "filename": "pixel.png",
            "size_bytes": 4,
            "content": b"\x89PNG",
        }
        values.update(overrides)
        return repo.create(**values)

    first = _create(filename="first.png")
    second = _create(filename="second.png")
    foreign_user = _create(user_id=other_user.id, filename="foreign-user.png")
    foreign_workspace = _create(
        workspace_id=other_workspace.id, filename="foreign-proj.png"
    )

    listed = repo.list_owned_by_ids(
        workspace_id=workspace.id,
        user_id=owner.id,
        attachment_ids=[
            first.id,
            second.id,
            foreign_user.id,
            foreign_workspace.id,
            uuid4(),
        ],
    )

    assert {item.id for item in listed} == {first.id, second.id}
    assert (
        repo.list_owned_by_ids(
            workspace_id=workspace.id,
            user_id=owner.id,
            attachment_ids=[],
        )
        == []
    )


def test_delete_removes_only_owned_attachment() -> None:
    session = _make_session()
    workspace = _make_workspace(session)
    owner = _make_user(session, "owner@example.com")
    other_user = _make_user(session, "other@example.com")
    repo = ChatAttachmentRepository(session)
    attachment = repo.create(
        workspace_id=workspace.id,
        user_id=owner.id,
        kind="document",
        mime="text/markdown",
        filename="notes.md",
        size_bytes=5,
        content=b"hello",
        extracted_text="hello",
    )

    wrong_user_delete = repo.delete(
        attachment_id=attachment.id,
        workspace_id=workspace.id,
        user_id=other_user.id,
    )
    deleted = repo.delete(
        attachment_id=attachment.id,
        workspace_id=workspace.id,
        user_id=owner.id,
    )

    assert wrong_user_delete is False
    assert deleted is True
    assert repo.get(attachment_id=attachment.id, workspace_id=workspace.id) is None
    assert (
        repo.delete(
            attachment_id=attachment.id,
            workspace_id=workspace.id,
            user_id=owner.id,
        )
        is False
    )
