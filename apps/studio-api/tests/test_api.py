from fastapi.testclient import TestClient

from app.main import app


def test_project_generation_flow() -> None:
    with TestClient(app) as client:
        created = client.post(
            "/api/projects",
            json={
                "mode_id": "reddit",
                "topic": "A basement door with one impossible rule",
                "language": "English",
                "duration": 45,
                "scenes": 7,
                "settings": {
                    "speaking_style": "mysterious",
                    "skip_research": True,
                },
            },
        )
        assert created.status_code == 201
        project_id = created.json()["id"]
        assert created.json()["status"] == "draft"

        generated = client.post(f"/api/projects/{project_id}/generate")
        assert generated.status_code == 200
        assert generated.json()["status"] == "ready"
        assert generated.json()["progress"] == 100
        assert generated.json()["output_url"]

        downloaded = client.get(f"/api/projects/{project_id}/download")
        assert downloaded.status_code == 200
        assert downloaded.headers["content-type"] == "video/mp4"

        logs = client.get(f"/api/projects/{project_id}/logs")
        assert logs.status_code == 200
        assert len(logs.json()["lines"]) >= 8


def test_unimplemented_mode_is_rejected() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/api/projects",
            json={
                "mode_id": "avatar",
                "topic": "A daily product update",
            },
        )
        assert response.status_code == 422


def test_lucky_prompt_returns_mode_specific_idea() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/api/prompts/lucky",
            json={
                "mode_id": "documentary",
                "language": "English",
                "niche": "history",
            },
        )
        assert response.status_code == 200
        assert response.json()["source"] == "fallback"
        assert 20 <= len(response.json()["prompt"]) <= 500
