from __future__ import annotations

import os
from pathlib import Path


WORKSPACE_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_ROOT = Path(
    os.getenv("STORYFORGE_RUNTIME_DIR", BACKEND_ROOT / "runtime")
).expanduser().resolve()
PROJECTS_ROOT = RUNTIME_ROOT / "projects"
DATABASE_PATH = RUNTIME_ROOT / "storyforge.sqlite3"

CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
CELERY_RESULT_BACKEND = os.getenv(
    "CELERY_RESULT_BACKEND", "redis://localhost:6379/1"
)
TASKS_EAGER = os.getenv("STORYFORGE_TASKS_EAGER", "false").lower() in {
    "1",
    "true",
    "yes",
}
MOCK_GENERATION = os.getenv("STORYFORGE_MOCK_GENERATION", "false").lower() in {
    "1",
    "true",
    "yes",
}
MOCK_STEP_SECONDS = float(os.getenv("STORYFORGE_MOCK_STEP_SECONDS", "0.35"))
MOCK_CONNECTIONS = os.getenv(
    "STORYFORGE_MOCK_CONNECTIONS", "false"
).lower() in {"1", "true", "yes"}

PUBLIC_API_URL = os.getenv("STORYFORGE_PUBLIC_API_URL", "http://localhost:8000").rstrip(
    "/"
)
FRONTEND_URL = os.getenv("STORYFORGE_FRONTEND_URL", "http://localhost:5173").rstrip(
    "/"
)
TOKEN_ENCRYPTION_KEY = os.getenv("STORYFORGE_TOKEN_ENCRYPTION_KEY", "")
YOUTUBE_CLIENT_ID = os.getenv("YOUTUBE_CLIENT_ID", "")
YOUTUBE_CLIENT_SECRET = os.getenv("YOUTUBE_CLIENT_SECRET", "")
TIKTOK_CLIENT_KEY = os.getenv("TIKTOK_CLIENT_KEY", "")
TIKTOK_CLIENT_SECRET = os.getenv("TIKTOK_CLIENT_SECRET", "")

STORYTELLER_ROOT = WORKSPACE_ROOT / "Storyteller"
EXPLAINER_ROOT = WORKSPACE_ROOT / "HistoicalEventExplainer"
PYTHON_EXECUTABLE = os.getenv("STORYFORGE_PYTHON", "python")

ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.getenv(
        "STORYFORGE_ALLOWED_ORIGINS",
        "http://localhost:4173,http://localhost:4174,http://localhost:5173",
    ).split(",")
    if origin.strip()
]


def ensure_runtime_directories() -> None:
    PROJECTS_ROOT.mkdir(parents=True, exist_ok=True)
