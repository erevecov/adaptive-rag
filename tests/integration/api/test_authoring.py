"""Tests de la superficie HTTP de authoring de projects/sources."""

from __future__ import annotations

from collections.abc import Iterator
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from adaptive_rag.api.app import create_app
from adaptive_rag.api.dependencies import get_session
from adaptive_rag.db.base import Base
from adaptive_rag.db.models import Project, Source
from adaptive_rag.db.repositories import ProjectRepository, SourceRepository
from adaptive_rag.db.session import create_session_factory


def _make_session() -> Session:
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine, tables=[Project.__table__, Source.__table__])
    return create_session_factory(engine)()


def _client(*, session: Session) -> TestClient:
    app = create_app()

    def override_session() -> Iterator[Session]:
        yield session

    app.dependency_overrides[get_session] = override_session
    return TestClient(app)


def test_create_project_defaults_to_dense_and_lists_projects() -> None:
    session = _make_session()
    client = _client(session=session)

    response = client.post("/projects", json={"name": "Demo"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["name"] == "Demo"
    assert payload["embedding_mode"] == "dense"
    assert payload["retrieval_contextualization_enabled"] is True
    assert payload["budget_config_json"] is None
    assert set(payload) == {
        "id",
        "name",
        "embedding_mode",
        "retrieval_contextualization_enabled",
        "budget_config_json",
        "created_at",
        "updated_at",
    }

    list_response = client.get("/projects")

    assert list_response.status_code == 200
    assert [item["id"] for item in list_response.json()["items"]] == [payload["id"]]


def test_get_project_returns_404_for_missing_project() -> None:
    client = _client(session=_make_session())

    response = client.get(f"/projects/{uuid4()}")

    assert response.status_code == 404
    assert response.json()["detail"] == "project not found"


def test_create_project_rejects_public_dense_sparse_mode() -> None:
    client = _client(session=_make_session())

    response = client.post(
        "/projects",
        json={"name": "Sparse", "embedding_mode": "dense_sparse"},
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "project embedding_mode must be dense"


def test_create_text_source_requires_content_and_lists_sources() -> None:
    session = _make_session()
    project = ProjectRepository(session).create(name="Demo")
    session.commit()
    client = _client(session=session)

    missing_content = client.post(
        f"/projects/{project.id}/sources",
        json={"source_type": "markdown", "external_id": "notes.md"},
    )

    assert missing_content.status_code == 422
    assert (
        missing_content.json()["detail"]
        == "markdown source requires extra_metadata.content"
    )

    response = client.post(
        f"/projects/{project.id}/sources",
        json={
            "source_type": "markdown",
            "external_id": "notes.md",
            "tags": ["docs", "local"],
            "extra_metadata": {"content": "# Notes"},
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["project_id"] == str(project.id)
    assert payload["source_type"] == "markdown"
    assert payload["external_id"] == "notes.md"
    assert payload["tags"] == ["docs", "local"]
    assert payload["extra_metadata"] == {"content": "# Notes"}
    assert set(payload) == {
        "id",
        "project_id",
        "source_type",
        "external_id",
        "tags",
        "extra_metadata",
        "created_at",
        "updated_at",
    }

    list_response = client.get(f"/projects/{project.id}/sources")

    assert list_response.status_code == 200
    assert [item["id"] for item in list_response.json()["items"]] == [
        payload["id"]
    ]


def test_create_url_source_does_not_require_content() -> None:
    session = _make_session()
    project = ProjectRepository(session).create(name="Demo")
    session.commit()
    client = _client(session=session)

    response = client.post(
        f"/projects/{project.id}/sources",
        json={
            "source_type": "url",
            "external_id": "https://example.com/article",
        },
    )

    assert response.status_code == 200
    assert response.json()["source_type"] == "url"
    assert response.json()["external_id"] == "https://example.com/article"
    assert response.json()["extra_metadata"] is None


def test_create_source_returns_409_for_duplicate_identity() -> None:
    session = _make_session()
    project = ProjectRepository(session).create(name="Demo")
    SourceRepository(session).create(
        project_id=project.id,
        source_type="url",
        external_id="https://example.com/article",
    )
    session.commit()
    client = _client(session=session)

    response = client.post(
        f"/projects/{project.id}/sources",
        json={
            "source_type": "url",
            "external_id": "https://example.com/article",
        },
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "source already exists"


def test_sources_are_scoped_to_project_for_list_and_get() -> None:
    session = _make_session()
    project_a = ProjectRepository(session).create(name="A")
    project_b = ProjectRepository(session).create(name="B")
    source_a = SourceRepository(session).create(
        project_id=project_a.id,
        source_type="url",
        external_id="https://example.com/a",
    )
    source_b = SourceRepository(session).create(
        project_id=project_b.id,
        source_type="url",
        external_id="https://example.com/b",
    )
    session.commit()
    client = _client(session=session)

    list_response = client.get(f"/projects/{project_a.id}/sources")
    cross_project_response = client.get(
        f"/projects/{project_a.id}/sources/{source_b.id}"
    )
    own_source_response = client.get(f"/projects/{project_a.id}/sources/{source_a.id}")

    assert list_response.status_code == 200
    assert [item["id"] for item in list_response.json()["items"]] == [
        str(source_a.id)
    ]
    assert cross_project_response.status_code == 404
    assert cross_project_response.json()["detail"] == "source not found"
    assert own_source_response.status_code == 200
    assert own_source_response.json()["id"] == str(source_a.id)


def test_create_source_rejects_unknown_project_and_source_type() -> None:
    client = _client(session=_make_session())
    project_id = uuid4()

    missing_project = client.post(
        f"/projects/{project_id}/sources",
        json={"source_type": "url", "external_id": "https://example.com"},
    )

    assert missing_project.status_code == 404
    assert missing_project.json()["detail"] == "project not found"

    session = _make_session()
    project = ProjectRepository(session).create(name="Demo")
    session.commit()
    client = _client(session=session)

    unsupported = client.post(
        f"/projects/{project.id}/sources",
        json={"source_type": "pdf", "external_id": "file.pdf"},
    )

    assert unsupported.status_code == 422
    assert (
        unsupported.json()["detail"]
        == "source_type must be one of markdown, text, txt, url"
    )
