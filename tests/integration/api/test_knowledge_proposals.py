"""Tests HTTP para propuestas de conocimiento originadas desde chat."""

from __future__ import annotations

from collections.abc import Iterator
from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from adaptive_rag.api.app import create_app
from adaptive_rag.api.dependencies import get_session
from adaptive_rag.auth import hash_access_token
from adaptive_rag.db.base import Base
from adaptive_rag.db.models import (
    ChatMessage,
    ChatSession,
    Job,
    JobEvent,
    KnowledgeProposal,
    Source,
    User,
    UserAccessToken,
    Workspace,
    WorkspaceMembership,
)
from adaptive_rag.db.repositories import (
    UserRepository,
    WorkspaceMembershipRepository,
    WorkspaceRepository,
)
from adaptive_rag.db.session import create_session_factory


def _make_session() -> Session:
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(
        engine,
        tables=[
            Workspace.__table__,
            User.__table__,
            UserAccessToken.__table__,
            WorkspaceMembership.__table__,
            Source.__table__,
            Job.__table__,
            JobEvent.__table__,
            ChatSession.__table__,
            ChatMessage.__table__,
            KnowledgeProposal.__table__,
        ],
    )
    return create_session_factory(engine)()


def _client(*, session: Session) -> TestClient:
    app = create_app()

    def override_session() -> Iterator[Session]:
        yield session

    app.dependency_overrides[get_session] = override_session
    return TestClient(app)


def _create_user(session: Session, *, email: str, token: str) -> User:
    repo = UserRepository(session)
    user = repo.create_user(email=email, display_name=email)
    repo.upsert_access_token(
        user_id=user.id,
        token_hash=hash_access_token(token),
        label=f"{email} token",
    )
    return user


def _grant(session: Session, *, workspace: Workspace, user: User, role: str) -> None:
    WorkspaceMembershipRepository(session).upsert_membership(
        workspace_id=workspace.id,
        user_id=user.id,
        role=role,
    )


def _bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_viewer_submit_creates_pending_knowledge_proposal() -> None:
    session = _make_session()
    workspace = WorkspaceRepository(session).create(name="Demo")
    viewer = _create_user(session, email="viewer@example.com", token="viewer-token")
    _grant(session, workspace=workspace, user=viewer, role="viewer")
    session.commit()
    client = _client(session=session)

    response = client.post(
        f"/workspaces/{workspace.id}/knowledge-proposals",
        headers=_bearer("viewer-token"),
        json={"proposed_text": "Viewer proposed knowledge"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "pending"
    assert payload["submitted_by_user_id"] == str(viewer.id)
    assert payload["proposed_text"] == "Viewer proposed knowledge"
    assert payload["approved_source_id"] is None
    assert session.query(KnowledgeProposal).count() == 1
    assert session.query(Job).count() == 0


def test_contributor_submit_enters_knowledge_directly_as_approved_source() -> None:
    session = _make_session()
    workspace = WorkspaceRepository(session).create(name="Demo")
    contributor = _create_user(
        session,
        email="contributor@example.com",
        token="contributor-token",
    )
    _grant(session, workspace=workspace, user=contributor, role="contributor")
    session.commit()
    client = _client(session=session)

    response = client.post(
        f"/workspaces/{workspace.id}/knowledge-proposals",
        headers=_bearer("contributor-token"),
        json={"proposed_text": "Contributor knowledge"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "approved"
    assert payload["reviewed_by_user_id"] == str(contributor.id)
    source = session.get(Source, UUID(payload["approved_source_id"]))
    assert source is not None
    assert source.source_type == "markdown"
    assert source.extra_metadata == {"content": "Contributor knowledge"}
    job = session.query(Job).one()
    assert job.job_type == "ingest_source"
    assert job.workspace_id == workspace.id
    assert job.payload_json == {"source_id": str(source.id)}


def test_contributor_can_list_refine_and_approve_pending_proposal() -> None:
    session = _make_session()
    workspace = WorkspaceRepository(session).create(name="Demo")
    viewer = _create_user(session, email="viewer@example.com", token="viewer-token")
    contributor = _create_user(
        session,
        email="contributor@example.com",
        token="contributor-token",
    )
    _grant(session, workspace=workspace, user=viewer, role="viewer")
    _grant(session, workspace=workspace, user=contributor, role="contributor")
    session.commit()
    client = _client(session=session)
    created = client.post(
        f"/workspaces/{workspace.id}/knowledge-proposals",
        headers=_bearer("viewer-token"),
        json={"proposed_text": "Draft knowledge"},
    ).json()

    pending = client.get(
        f"/workspaces/{workspace.id}/knowledge-proposals",
        headers=_bearer("contributor-token"),
        params={"status": "pending"},
    )
    refined = client.post(
        f"/workspaces/{workspace.id}/knowledge-proposals/{created['id']}/refine",
        headers=_bearer("contributor-token"),
        json={"refined_text": "Refined knowledge"},
    )
    approved = client.post(
        f"/workspaces/{workspace.id}/knowledge-proposals/{created['id']}/approve",
        headers=_bearer("contributor-token"),
        json={"review_note": "accepted"},
    )

    assert pending.status_code == 200
    assert [item["id"] for item in pending.json()["items"]] == [created["id"]]
    assert refined.status_code == 200
    assert refined.json()["refined_text"] == "Refined knowledge"
    assert approved.status_code == 200
    approved_payload = approved.json()
    assert approved_payload["status"] == "approved"
    assert approved_payload["review_note"] == "accepted"
    source = session.get(Source, UUID(approved_payload["approved_source_id"]))
    assert source is not None
    assert source.extra_metadata == {"content": "Refined knowledge"}
    job = session.query(Job).one()
    assert job.job_type == "ingest_source"
    assert job.payload_json == {"source_id": str(source.id)}


def test_contributor_can_reject_pending_proposal_with_reason() -> None:
    session = _make_session()
    workspace = WorkspaceRepository(session).create(name="Demo")
    viewer = _create_user(session, email="viewer@example.com", token="viewer-token")
    contributor = _create_user(
        session,
        email="contributor@example.com",
        token="contributor-token",
    )
    _grant(session, workspace=workspace, user=viewer, role="viewer")
    _grant(session, workspace=workspace, user=contributor, role="contributor")
    session.commit()
    client = _client(session=session)
    created = client.post(
        f"/workspaces/{workspace.id}/knowledge-proposals",
        headers=_bearer("viewer-token"),
        json={"proposed_text": "Weak knowledge"},
    ).json()

    rejected = client.post(
        f"/workspaces/{workspace.id}/knowledge-proposals/{created['id']}/reject",
        headers=_bearer("contributor-token"),
        json={"reason": "not supported"},
    )
    approve_after_reject = client.post(
        f"/workspaces/{workspace.id}/knowledge-proposals/{created['id']}/approve",
        headers=_bearer("contributor-token"),
        json={},
    )

    assert rejected.status_code == 200
    assert rejected.json()["status"] == "rejected"
    assert rejected.json()["review_note"] == "not supported"
    assert session.query(Job).count() == 0
    assert approve_after_reject.status_code == 422
    assert approve_after_reject.json()["detail"] == "knowledge_proposal_not_pending"


def test_viewer_cannot_review_workspace_knowledge_proposals() -> None:
    session = _make_session()
    workspace = WorkspaceRepository(session).create(name="Demo")
    viewer = _create_user(session, email="viewer@example.com", token="viewer-token")
    _grant(session, workspace=workspace, user=viewer, role="viewer")
    session.commit()
    client = _client(session=session)

    response = client.get(
        f"/workspaces/{workspace.id}/knowledge-proposals",
        headers=_bearer("viewer-token"),
    )

    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "workspace_contributor_required"
