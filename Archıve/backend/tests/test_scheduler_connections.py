from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from app.main import app


def create_draft(client: TestClient) -> dict:
    response = client.post(
        "/api/projects",
        json={
            "mode_id": "ai-photos",
            "topic": "A scheduled story about a forgotten observatory",
            "duration": 30,
            "scenes": 4,
        },
    )
    assert response.status_code == 201
    return response.json()


def test_schedule_run_now_dispatches_generation() -> None:
    with TestClient(app) as client:
        project = create_draft(client)
        scheduled = client.post(
            "/api/schedules",
            json={
                "project_id": project["id"],
                "run_at": (datetime.now(UTC) + timedelta(hours=1)).isoformat(),
                "timezone": "Europe/Istanbul",
            },
        )
        assert scheduled.status_code == 201
        schedule_id = scheduled.json()["id"]
        assert scheduled.json()["status"] == "scheduled"

        triggered = client.post(f"/api/schedules/{schedule_id}/run-now")
        assert triggered.status_code == 200
        assert triggered.json()["status"] == "triggered"

        generated = client.get(f"/api/projects/{project['id']}")
        assert generated.json()["status"] == "ready"


def test_mock_connection_can_connect_and_disconnect() -> None:
    with TestClient(app) as client:
        providers = {
            connection["provider"]: connection
            for connection in client.get("/api/connections").json()
        }
        assert providers["youtube"]["available"] is True
        assert providers["tiktok"]["available"] is True
        assert providers["instagram"]["available"] is False
        assert providers["instagram"]["availability_note"] == (
            "Publishing connector planned"
        )
        unavailable = client.post("/api/connections/instagram/connect")
        assert unavailable.status_code == 503

        connected = client.post("/api/connections/youtube/connect")
        assert connected.status_code == 200
        assert connected.json()["connection"]["status"] == "connected"

        disconnected = client.delete("/api/connections/youtube")
        assert disconnected.status_code == 200
        assert disconnected.json()["status"] == "disconnected"
