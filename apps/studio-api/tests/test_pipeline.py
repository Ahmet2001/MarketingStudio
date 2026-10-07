from app.pipeline import build_pipeline_command


def project(mode_id: str) -> dict:
    return {
        "id": "abc123",
        "mode_id": mode_id,
        "topic": "A test story",
        "language": "English",
        "duration": 45,
        "scenes": 7,
        "settings": {
            "niche": "history",
            "skip_research": False,
            "research_region": "tr-tr",
            "speaking_style": "mysterious",
            "speech_speed": 0.85,
            "character_style": "animated-human",
            "voice_id": None,
            "real_photo_min_match": 75,
            "ai_provider": "fal",
            "ai_model_identifier": "fal-ai/flux/schnell",
            "ai_model_config": {
                "image_size": "portrait_16_9",
                "num_inference_steps": 4,
            },
        },
    }


def test_reddit_mode_enables_gameplay() -> None:
    command, _ = build_pipeline_command(project("reddit"))
    assert "--video-game-mode" in command
    assert "--gameplay-video" in command
    assert "--speech-speed" in command
    assert "--image-provider" not in command


def test_ai_photo_mode_passes_model_snapshot_to_worker() -> None:
    command, _ = build_pipeline_command(project("ai-photos"))
    assert command[command.index("--image-provider") + 1] == "fal"
    assert command[command.index("--image-model") + 1] == "fal-ai/flux/schnell"
    assert "portrait_16_9" in command[command.index("--image-config-json") + 1]


def test_ai_photo_mode_supports_together_provider() -> None:
    value = project("ai-photos")
    value["settings"]["ai_provider"] = "together"
    value["settings"]["ai_model_identifier"] = (
        "black-forest-labs/FLUX.1-schnell"
    )
    value["settings"]["ai_model_config"] = {
        "aspect_ratio": "9:16",
        "steps": 4,
    }
    command, _ = build_pipeline_command(value)
    assert command[command.index("--image-provider") + 1] == "together"
    assert (
        command[command.index("--image-model") + 1]
        == "black-forest-labs/FLUX.1-schnell"
    )


def test_ai_photo_mode_supports_gemini_image_provider() -> None:
    value = project("ai-photos")
    value["settings"]["ai_provider"] = "gemini"
    value["settings"]["ai_model_identifier"] = "gemini-2.5-flash-image"
    value["settings"]["ai_model_config"] = {
        "responseModalities": ["IMAGE"],
        "responseFormat": {"image": {"aspectRatio": "9:16"}},
    }
    command, _ = build_pipeline_command(value)
    assert command[command.index("--image-provider") + 1] == "gemini"
    assert (
        command[command.index("--image-model") + 1]
        == "gemini-2.5-flash-image"
    )


def test_documentary_mode_uses_authentic_images() -> None:
    command, _ = build_pipeline_command(project("documentary"))
    assert "--visual-source" in command
    assert command[command.index("--visual-source") + 1] == "real"
    assert "--real-photo-min-match" in command
