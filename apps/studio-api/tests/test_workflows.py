from fastapi.testclient import TestClient

from app.main import app


def workflow_payload() -> dict:
    return {
        "name": "Daily mystery automation",
        "status": "active",
        "nodes": [
            {
                "id": "generator-1",
                "kind": "content-generator",
                "subtype": "ai-photos",
                "label": "Storyteller with AI photos",
                "x": 80,
                "y": 180,
                "config": {
                    "topic": "",
                    "duration": 30,
                    "scenes": 4,
                    "language": "English",
                    "niche": "mystery",
                },
            },
            {
                "id": "scheduler-1",
                "kind": "scheduler",
                "subtype": "delay",
                "label": "Schedule",
                "x": 390,
                "y": 180,
                "config": {
                    "delay_minutes": 5,
                    "timezone": "Europe/Istanbul",
                },
            },
        ],
        "edges": [
            {
                "id": "edge-1",
                "source": "generator-1",
                "target": "scheduler-1",
            }
        ],
    }


def test_workflow_can_be_saved_updated_and_run() -> None:
    with TestClient(app) as client:
        created = client.post("/api/workflows", json=workflow_payload())
        assert created.status_code == 201
        workflow_id = created.json()["id"]

        updated_payload = workflow_payload()
        updated_payload["name"] = "Updated mystery automation"
        updated = client.put(
            f"/api/workflows/{workflow_id}",
            json=updated_payload,
        )
        assert updated.status_code == 200
        assert updated.json()["name"] == "Updated mystery automation"

        run = client.post(f"/api/workflows/{workflow_id}/run")
        assert run.status_code == 200
        assert run.json()["status"] == "scheduled"
        assert run.json()["project_id"]
        assert run.json()["schedule_id"]

        workflows = client.get("/api/workflows")
        assert workflows.status_code == 200
        saved = next(
            item
            for item in workflows.json()["items"]
            if item["id"] == workflow_id
        )
        assert saved["last_run_status"] == "scheduled"


def test_workflow_requires_one_generator() -> None:
    with TestClient(app) as client:
        payload = workflow_payload()
        payload["nodes"] = payload["nodes"][1:]
        payload["edges"] = []
        created = client.post("/api/workflows", json=payload)
        response = client.post(
            f"/api/workflows/{created.json()['id']}/run"
        )
        assert response.status_code == 422
