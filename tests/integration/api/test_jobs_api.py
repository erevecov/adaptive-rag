"""RBAC, isolation, pagination, and lifecycle APIs for background jobs."""

from uuid import uuid4

from _job_api_support import bearer, make_job_api_setup
from pydantic import BaseModel, ConfigDict

from adaptive_rag.api.dependencies import get_job_registry
from adaptive_rag.jobs import JobHandlerDefinition, JobRegistry


def test_generic_mutations_require_workspace_admin() -> None:
    setup = make_job_api_setup()
    url = f"/workspaces/{setup.workspace.id}/jobs"
    body = {
        "job_type": "ingest_source",
        "handler_version": 1,
        "payload": {"source_id": str(uuid4())},
    }

    viewer = setup.client.post(url, json=body, headers=bearer(setup.viewer_token))
    contributor = setup.client.post(
        url, json=body, headers=bearer(setup.contributor_token)
    )
    admin = setup.client.post(url, json=body, headers=bearer(setup.admin_token))

    assert viewer.status_code == 403
    assert contributor.status_code == 403
    assert admin.status_code == 201
    assert admin.json()["created"] is True
    assert admin.json()["job"]["scope"] == "workspace"


def test_system_jobs_are_superadmin_only() -> None:
    setup = make_job_api_setup()

    workspace_admin = setup.client.get(
        "/admin/jobs?scope=system",
        headers=bearer(setup.admin_token),
    )
    superadmin = setup.client.get(
        "/admin/jobs?scope=system",
        headers=bearer(setup.superadmin_token),
    )

    assert workspace_admin.status_code == 403
    assert superadmin.status_code == 200
    assert superadmin.json()["items"] == []


def test_system_job_list_rejects_workspace_id_parameter() -> None:
    setup = make_job_api_setup()

    response = setup.client.get(
        f"/admin/jobs?scope=system&workspace_id={setup.workspace.id}",
        headers=bearer(setup.superadmin_token),
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "workspace_id is not allowed for system scope"


def test_superadmin_can_enqueue_inspect_and_cancel_system_job() -> None:
    setup = make_job_api_setup()
    headers = bearer(setup.superadmin_token)

    created = setup.client.post(
        "/admin/jobs",
        json={"job_type": "provider_model_pricing_sync", "payload": {}},
        headers=headers,
    )
    job = created.json()["job"]
    detail = setup.client.get(f"/admin/jobs/{job['id']}", headers=headers)
    cancelled = setup.client.post(
        f"/admin/jobs/{job['id']}/cancel",
        json={"version": job["version"]},
        headers=headers,
    )

    assert created.status_code == 201
    assert job["scope"] == "system"
    assert detail.status_code == 200
    assert detail.json()["job"]["id"] == job["id"]
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "cancelled"


def test_superadmin_can_list_workspace_job_handlers() -> None:
    setup = make_job_api_setup()

    response = setup.client.get(
        f"/workspaces/{setup.workspace.id}/job-handlers",
        headers=bearer(setup.superadmin_token),
    )

    assert response.status_code == 200
    assert [handler["name"] for handler in response.json()] == ["ingest_source"]


def test_idempotent_reuse_and_stale_cancel_conflict() -> None:
    setup = make_job_api_setup()
    url = f"/workspaces/{setup.workspace.id}/jobs"
    body = {
        "job_type": "ingest_source",
        "handler_version": 1,
        "payload": {"source_id": str(uuid4())},
        "idempotency_key": "api-idempotency",
    }
    first = setup.client.post(url, json=body, headers=bearer(setup.admin_token))
    second = setup.client.post(url, json=body, headers=bearer(setup.admin_token))
    job = first.json()["job"]

    stale = setup.client.post(
        f"{url}/{job['id']}/cancel",
        json={"version": job["version"] + 1},
        headers=bearer(setup.admin_token),
    )

    assert first.status_code == 201
    assert second.status_code == 200
    assert second.json()["created"] is False
    assert second.json()["job"]["id"] == job["id"]
    assert stale.status_code == 409


def test_workspace_reads_cannot_cross_scope() -> None:
    setup = make_job_api_setup()
    other_workspace_id = uuid4()

    response = setup.client.get(
        f"/workspaces/{other_workspace_id}/jobs",
        headers=bearer(setup.admin_token),
    )

    assert response.status_code == 404


def test_workspace_job_list_accepts_stable_queue_filter_alias() -> None:
    setup = make_job_api_setup()
    base_url = f"/workspaces/{setup.workspace.id}/jobs"
    for queue_name in ("ingestion", "default"):
        response = setup.client.post(
            base_url,
            json={
                "job_type": "ingest_source",
                "payload": {"source_id": str(uuid4())},
                "queue_name": queue_name,
            },
            headers=bearer(setup.admin_token),
        )
        assert response.status_code == 201

    response = setup.client.get(
        f"{base_url}?queue=default", headers=bearer(setup.viewer_token)
    )

    assert response.status_code == 200
    assert [item["queue_name"] for item in response.json()["items"]] == ["default"]


def test_job_detail_uses_handler_redaction() -> None:
    setup = make_job_api_setup()

    class MessagePayload(BaseModel):
        model_config = ConfigDict(extra="forbid")

        message: str

    registry = JobRegistry()
    registry.register(
        JobHandlerDefinition(
            name="redacted_message",
            version=1,
            payload_model=MessagePayload,
            handler=lambda _context, payload: {"message": payload.message},
            queue_name="default",
            allowed_scopes=frozenset({"workspace"}),
            allow_manual_enqueue=True,
            redact_payload=lambda _value: {"message": "[REDACTED]"},
        )
    )
    setup.client.app.dependency_overrides[get_job_registry] = lambda: registry
    base_url = f"/workspaces/{setup.workspace.id}/jobs"
    created = setup.client.post(
        base_url,
        json={
            "job_type": "redacted_message",
            "payload": {"message": "sensitive"},
        },
        headers=bearer(setup.admin_token),
    ).json()

    detail = setup.client.get(
        f"{base_url}/{created['job']['id']}",
        headers=bearer(setup.viewer_token),
    )

    assert detail.status_code == 200
    assert detail.json()["job"]["payload_json"] == {"message": "[REDACTED]"}


def test_superadmin_operational_surfaces_are_bounded() -> None:
    setup = make_job_api_setup()
    headers = bearer(setup.superadmin_token)

    queues = setup.client.get("/admin/job-queues", headers=headers)
    workers = setup.client.get("/admin/job-workers", headers=headers)
    metrics = setup.client.get("/admin/job-metrics", headers=headers)

    assert queues.status_code == 200
    assert len(queues.json()) == 3
    assert workers.status_code == 200
    assert workers.json() == []
    assert metrics.status_code == 200
    assert len(metrics.json()["queues"]) == 3


def test_superadmin_can_clear_queue_concurrency_limits() -> None:
    setup = make_job_api_setup()
    headers = bearer(setup.superadmin_token)
    queue = setup.client.get("/admin/job-queues/default", headers=headers).json()
    configured = setup.client.patch(
        "/admin/job-queues/default",
        json={"global_concurrency_limit": 3, "version": queue["version"]},
        headers=headers,
    ).json()

    cleared = setup.client.patch(
        "/admin/job-queues/default",
        json={
            "global_concurrency_limit": None,
            "version": configured["version"],
        },
        headers=headers,
    )

    assert cleared.status_code == 200
    assert cleared.json()["global_concurrency_limit"] is None
