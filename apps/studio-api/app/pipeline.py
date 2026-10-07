from __future__ import annotations

import json
import os
import re
import selectors
import signal
import subprocess
import time
from pathlib import Path
from typing import Any

from .ai_providers import get_api_key, require_ai_provider
from .config import (
    EXPLAINER_ROOT,
    MOCK_GENERATION,
    MOCK_STEP_SECONDS,
    PYTHON_EXECUTABLE,
    STORYTELLER_ROOT,
)
from .repository import (
    is_cancel_requested,
    project_directory,
    project_log_path,
    update_project,
)


PROGRESS_PATTERN = re.compile(r"\b([1-8])/8\b")
STAGES = {
    1: "Preparing project",
    2: "Researching sources",
    3: "Writing the script",
    4: "Creating the cover",
    5: "Preparing visuals",
    6: "Generating narration",
    7: "Rendering scenes",
    8: "Finalizing video",
}


class ProjectCancelled(RuntimeError):
    pass


def build_pipeline_command(project: dict[str, Any]) -> tuple[list[str], Path]:
    settings = project["settings"]
    output_dir = project_directory(project["id"]) / "outputs"
    common = [
        project["topic"],
        "--language",
        project["language"],
        "--duration",
        str(project["duration"]),
        "--scenes",
        str(project["scenes"]),
        "--output-dir",
        str(output_dir),
        "--research-region",
        settings["research_region"],
    ]

    if project["mode_id"] in {"ai-photos", "reddit"}:
        command = [
            PYTHON_EXECUTABLE,
            str(STORYTELLER_ROOT / "main.py"),
            *common,
            "--niche",
            settings["niche"],
            "--speaking-style",
            settings["speaking_style"],
            "--character-style",
            settings["character_style"],
            "--skip-cover",
        ]
        if settings.get("speech_speed") is not None:
            command.extend(["--speech-speed", str(settings["speech_speed"])])
        if settings.get("voice_id"):
            command.extend(["--voice-id", settings["voice_id"]])
        if project["mode_id"] == "ai-photos" and settings.get(
            "ai_model_identifier"
        ):
            command.extend(
                [
                    "--image-provider",
                    settings["ai_provider"],
                    "--image-model",
                    settings["ai_model_identifier"],
                    "--image-config-json",
                    json.dumps(settings.get("ai_model_config") or {}),
                ]
            )
        if settings["skip_research"]:
            command.append("--skip-research")
        if project["mode_id"] == "reddit":
            command.extend(
                [
                    "--video-game-mode",
                    "--gameplay-video",
                    str(STORYTELLER_ROOT / "gameplay"),
                ]
            )
        return command, STORYTELLER_ROOT

    if project["mode_id"] in {"real-images", "documentary"}:
        command = [
            PYTHON_EXECUTABLE,
            str(EXPLAINER_ROOT / "main.py"),
            *common,
            "--visual-source",
            "real",
            "--real-photo-min-match",
            str(settings["real_photo_min_match"]),
            "--skip-cover",
        ]
        if settings.get("voice_id"):
            command.extend(["--voice-id", settings["voice_id"]])
        if settings["skip_research"]:
            command.append("--skip-research")
        return command, EXPLAINER_ROOT

    raise ValueError(f"No generation worker exists for mode {project['mode_id']!r}.")


def find_final_video(project_id: str) -> Path:
    output_root = project_directory(project_id) / "outputs"
    candidates = [
        path
        for path in output_root.rglob("*.mp4")
        if path.name != "joined.mp4" and "clips" not in path.parts
    ]
    if not candidates:
        raise FileNotFoundError("The pipeline completed without a final MP4.")
    return max(candidates, key=lambda path: (path.stat().st_mtime, path.stat().st_size))


def _append_log(project_id: str, line: str) -> None:
    path = project_log_path(project_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as log_file:
        log_file.write(f"{line.rstrip()}\n")


def _update_progress_from_line(project_id: str, line: str) -> None:
    match = PROGRESS_PATTERN.search(line)
    if not match:
        return
    step = int(match.group(1))
    update_project(
        project_id,
        status="generating",
        stage=STAGES[step],
        progress=min(94, 5 + step * 11),
    )


def _terminate_process(process: subprocess.Popen[str]) -> None:
    if process.poll() is not None:
        return
    try:
        os.killpg(process.pid, signal.SIGTERM)
        process.wait(timeout=8)
    except (ProcessLookupError, subprocess.TimeoutExpired):
        if process.poll() is None:
            os.killpg(process.pid, signal.SIGKILL)


def run_real_pipeline(project: dict[str, Any]) -> Path:
    project_id = project["id"]
    command, working_directory = build_pipeline_command(project)
    _append_log(project_id, f"Starting {project['mode']} pipeline.")
    _append_log(project_id, f"Worker directory: {working_directory}")
    process_environment = os.environ.copy()
    provider_id = project["settings"].get("ai_provider")
    if provider_id:
        api_key = get_api_key(provider_id)
        if api_key:
            provider = require_ai_provider(provider_id)
            process_environment[provider.environment_variable] = api_key
    process = subprocess.Popen(
        command,
        cwd=working_directory,
        env=process_environment,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        start_new_session=True,
    )
    if process.stdout is None:
        raise RuntimeError("Could not capture pipeline output.")

    selector = selectors.DefaultSelector()
    selector.register(process.stdout, selectors.EVENT_READ)
    try:
        while process.poll() is None:
            if is_cancel_requested(project_id):
                _append_log(project_id, "Cancellation requested.")
                _terminate_process(process)
                raise ProjectCancelled("Generation was cancelled.")
            for key, _ in selector.select(timeout=0.75):
                line = key.fileobj.readline()
                if line:
                    _append_log(project_id, line)
                    _update_progress_from_line(project_id, line)

        for line in process.stdout:
            _append_log(project_id, line)
            _update_progress_from_line(project_id, line)
    finally:
        selector.close()

    if process.returncode != 0:
        raise RuntimeError(
            f"Pipeline exited with status {process.returncode}. Check generation logs."
        )
    return find_final_video(project_id)


def run_mock_pipeline(project: dict[str, Any]) -> Path:
    project_id = project["id"]
    for step in range(1, 9):
        if is_cancel_requested(project_id):
            raise ProjectCancelled("Generation was cancelled.")
        stage = STAGES[step]
        _append_log(project_id, f"{step}/8 {stage} (mock)")
        update_project(
            project_id,
            status="generating",
            stage=stage,
            progress=min(94, 5 + step * 11),
        )
        time.sleep(MOCK_STEP_SECONDS)

    output_directory = project_directory(project_id) / "outputs" / "mock"
    output_directory.mkdir(parents=True, exist_ok=True)
    output_path = output_directory / "storyforge-preview.mp4"
    command = [
        "ffmpeg",
        "-y",
        "-f",
        "lavfi",
        "-i",
        "color=c=#2b2031:s=360x640:d=2",
        "-f",
        "lavfi",
        "-i",
        "sine=frequency=440:duration=2",
        "-vf",
        (
            "drawtext=text='STORYFORGE PREVIEW':fontcolor=white:"
            "fontsize=22:x=(w-text_w)/2:y=(h-text_h)/2"
        ),
        "-shortest",
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        str(output_path),
    ]
    completed = subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        _append_log(project_id, completed.stderr)
        raise RuntimeError("Mock preview rendering failed.")
    return output_path


def run_pipeline(project: dict[str, Any]) -> Path:
    return run_mock_pipeline(project) if MOCK_GENERATION else run_real_pipeline(project)
