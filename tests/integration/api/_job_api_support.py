"""Shared isolated API setup for background-job control-plane tests."""

from dataclasses import dataclass

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from adaptive_rag.api.app import create_app
from adaptive_rag.api.dependencies import get_session
from adaptive_rag.auth import hash_access_token
from adaptive_rag.db.base import Base
from adaptive_rag.db.models import (
    Job,
    JobAttempt,
    JobEvent,
    JobQueue,
    JobQueueWorkspaceState,
    JobSchedule,
    JobWorker,
    User,
    UserAccessToken,
    Workspace,
    WorkspaceMembership,
)
from adaptive_rag.db.session import create_session_factory


@dataclass(frozen=True, slots=True)
class JobApiSetup:
    client: TestClient
    session: Session
    workspace: Workspace
    viewer_token: str
    contributor_token: str
    admin_token: str
    superadmin_token: str


def make_job_api_setup() -> JobApiSetup:
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
            JobQueue.__table__,
            JobSchedule.__table__,
            Job.__table__,
            JobAttempt.__table__,
            JobEvent.__table__,
            JobQueueWorkspaceState.__table__,
            JobWorker.__table__,
        ],
    )
    session = create_session_factory(engine)()
    workspace = Workspace(name="jobs-api")
    session.add(workspace)
    session.add_all(
        [JobQueue(name="default"), JobQueue(name="ingestion"), JobQueue(name="system")]
    )
    session.flush()
    tokens = {
        "viewer": "jobs-viewer-token",
        "contributor": "jobs-contributor-token",
        "admin": "jobs-admin-token",
        "superadmin": "jobs-superadmin-token",
    }
    for role, token in tokens.items():
        user = User(
            email=f"{role}@example.test",
            display_name=role,
            system_role="superadmin" if role == "superadmin" else "user",
        )
        session.add(user)
        session.flush()
        session.add(
            UserAccessToken(
                user_id=user.id,
                token_hash=hash_access_token(token),
                label="test",
            )
        )
        if role != "superadmin":
            session.add(
                WorkspaceMembership(
                    workspace_id=workspace.id,
                    user_id=user.id,
                    role=role,
                )
            )
    session.commit()
    app = create_app()

    def override_session():
        yield session

    app.dependency_overrides[get_session] = override_session
    return JobApiSetup(
        client=TestClient(app),
        session=session,
        workspace=workspace,
        viewer_token=tokens["viewer"],
        contributor_token=tokens["contributor"],
        admin_token=tokens["admin"],
        superadmin_token=tokens["superadmin"],
    )


def bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}
