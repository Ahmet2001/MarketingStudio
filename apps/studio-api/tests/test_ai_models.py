from fastapi.testclient import TestClient

from app.main import app


def test_provider_keys_and_model_presets_are_private_and_selectable() -> None:
    with TestClient(app) as client:
        saved_provider = client.put(
            "/api/ai/providers/fal",
            json={"api_key": "fal-secret-test-key-1234"},
        )
        assert saved_provider.status_code == 200
        assert saved_provider.json()["configured"] is True
        assert saved_provider.json()["key_hint"].endswith("1234")
        assert "fal-secret-test-key" not in saved_provider.text

        providers = client.get("/api/ai/providers")
        assert providers.status_code == 200
        assert "fal-secret-test-key" not in providers.text

        created_model = client.post(
            "/api/ai/models",
            json={
                "name": "My fal FLUX",
                "provider": "fal",
                "model_identifier": "fal-ai/flux/schnell",
                "configuration": {
                    "image_size": "portrait_16_9",
                    "num_inference_steps": 4,
                    "output_format": "png",
                },
                "enabled": True,
                "is_default": False,
            },
        )
        assert created_model.status_code == 201
        model_id = created_model.json()["id"]

        project = client.post(
            "/api/projects",
            json={
                "mode_id": "ai-photos",
                "topic": "A lighthouse that remembers every lost ship",
                "settings": {"ai_model_id": model_id},
            },
        )
        assert project.status_code == 201
        settings = project.json()["settings"]
        assert settings["ai_provider"] == "fal"
        assert settings["ai_model_identifier"] == "fal-ai/flux/schnell"
        assert settings["ai_model_config"]["image_size"] == "portrait_16_9"

        deleted = client.delete(f"/api/ai/models/{model_id}")
        assert deleted.status_code == 200

        removed_provider = client.delete("/api/ai/providers/fal")
        assert removed_provider.status_code == 200
        assert removed_provider.json()["configured"] is False


def test_together_provider_and_builtin_model_are_available() -> None:
    with TestClient(app) as client:
        saved = client.put(
            "/api/ai/providers/together",
            json={"api_key": "together-test-key-9876"},
        )
        assert saved.status_code == 200
        assert saved.json()["name"] == "Together AI"
        assert saved.json()["key_hint"].endswith("9876")
        assert "together-test-key" not in saved.text

        models = client.get("/api/ai/models")
        assert models.status_code == 200
        together_model = next(
            model
            for model in models.json()["items"]
            if model["id"] == "preset-together-flux-schnell"
        )
        assert together_model["provider"] == "together"
        assert together_model["model_identifier"] == (
            "black-forest-labs/FLUX.1-schnell"
        )

        removed = client.delete("/api/ai/providers/together")
        assert removed.status_code == 200
        assert removed.json()["configured"] is False


def test_gemini_image_provider_and_builtin_model_are_available() -> None:
    with TestClient(app) as client:
        saved = client.put(
            "/api/ai/providers/gemini",
            json={"api_key": "gemini-test-key-4321"},
        )
        assert saved.status_code == 200
        assert saved.json()["name"] == "Google Gemini"
        assert saved.json()["key_hint"].endswith("4321")
        assert "gemini-test-key" not in saved.text

        models = client.get("/api/ai/models")
        assert models.status_code == 200
        gemini_model = next(
            model
            for model in models.json()["items"]
            if model["id"] == "preset-gemini-25-flash-image"
        )
        assert gemini_model["provider"] == "gemini"
        assert gemini_model["model_identifier"] == "gemini-2.5-flash-image"
        assert (
            gemini_model["configuration"]["responseFormat"]["image"][
                "aspectRatio"
            ]
            == "9:16"
        )

        removed = client.delete("/api/ai/providers/gemini")
        assert removed.status_code == 200
        assert removed.json()["configured"] is False
