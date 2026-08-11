"""Workspace schedule CRUD and optimistic action APIs."""

from _job_api_support import bearer, make_job_api_setup


def test_workspace_admin_creates_pauses_and_runs_schedule_now() -> None:
    setup = make_job_api_setup()
    url = f"/workspaces/{setup.workspace.id}/job-schedules"
    body = {
        "name": "daily ingest",
        "job_type": "ingest_source",
        "handler_version": 1,
        "payload": {"source_id": "00000000-0000-0000-0000-000000000123"},
        "cron_expression": "0 3 * * *",
        "timezone": "UTC",
    }

    created = setup.client.post(url, json=body, headers=bearer(setup.admin_token))
    schedule = created.json()
    paused = setup.client.post(
        f"{url}/{schedule['id']}/pause",
        json={"version": schedule["version"]},
        headers=bearer(setup.admin_token),
    )
    run_now = setup.client.post(
        f"{url}/{schedule['id']}/run-now",
        json={"version": paused.json()["version"]},
        headers=bearer(setup.admin_token),
    )

    assert created.status_code == 201
    assert paused.status_code == 200
    assert paused.json()["paused_at"] is not None
    assert run_now.status_code == 201
    assert run_now.json()["schedule_id"] == schedule["id"]
    assert run_now.json()["scheduled_for"] is None


def test_stale_schedule_version_returns_conflict() -> None:
    setup = make_job_api_setup()
    url = f"/workspaces/{setup.workspace.id}/job-schedules"
    created = setup.client.post(
        url,
        json={
            "name": "hourly",
            "job_type": "ingest_source",
            "payload": {"source_id": "00000000-0000-0000-0000-000000000456"},
            "cron_expression": "0 * * * *",
            "timezone": "UTC",
        },
        headers=bearer(setup.admin_token),
    ).json()

    response = setup.client.post(
        f"{url}/{created['id']}/pause",
        json={"version": created["version"] + 1},
        headers=bearer(setup.admin_token),
    )

    assert response.status_code == 409


def test_superadmin_controls_system_schedules() -> None:
    setup = make_job_api_setup()
    headers = bearer(setup.superadmin_token)
    url = "/admin/job-schedules"

    created = setup.client.post(
        url,
        json={
            "name": "system pricing refresh",
            "job_type": "provider_model_pricing_sync",
            "payload": {},
            "cron_expression": "0 2 * * *",
            "timezone": "UTC",
        },
        headers=headers,
    )
    schedule = created.json()
    paused = setup.client.post(
        f"{url}/{schedule['id']}/pause",
        json={"version": schedule["version"]},
        headers=headers,
    )
    listed = setup.client.get(url, headers=headers)

    assert created.status_code == 201
    assert schedule["scope"] == "system"
    assert paused.status_code == 200
    assert paused.json()["paused_at"] is not None
    assert schedule["id"] in {item["id"] for item in listed.json()["items"]}
