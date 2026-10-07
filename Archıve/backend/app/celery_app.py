from celery import Celery

from .config import (
    CELERY_BROKER_URL,
    CELERY_RESULT_BACKEND,
    TASKS_EAGER,
    ensure_runtime_directories,
)

ensure_runtime_directories()

celery_app = Celery(
    "storyforge",
    broker=CELERY_BROKER_URL,
    backend=CELERY_RESULT_BACKEND,
    include=["app.tasks"],
)
celery_app.conf.update(
    task_track_started=True,
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    broker_connection_retry_on_startup=True,
    task_always_eager=TASKS_EAGER,
    task_eager_propagates=True,
    timezone="UTC",
    beat_schedule={
        "dispatch-due-storyforge-schedules": {
            "task": "storyforge.scheduler_tick",
            "schedule": 15.0,
        }
    },
)
