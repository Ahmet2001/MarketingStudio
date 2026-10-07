from __future__ import annotations

from .celery_app import celery_app
from .pipeline import ProjectCancelled, run_pipeline
from .repository import (
    claim_due_schedules,
    get_project,
    reset_for_generation,
    update_project,
    update_schedule,
)


@celery_app.task(bind=True, name="storyforge.generate_project")
def generate_project(self, project_id: str) -> dict[str, str]:
    project = get_project(project_id)
    if project is None:
        raise KeyError(f"Unknown project: {project_id}")

    update_project(
        project_id,
        task_id=self.request.id,
        status="generating",
        stage="Starting generation",
        progress=4,
        error=None,
    )
    try:
        output_path = run_pipeline(project)
    except ProjectCancelled as exc:
        update_project(
            project_id,
            status="cancelled",
            stage="Cancelled",
            progress=0,
            error=str(exc),
        )
        return {"project_id": project_id, "status": "cancelled"}
    except Exception as exc:
        update_project(
            project_id,
            status="failed",
            stage="Generation failed",
            error=str(exc)[:500],
        )
        raise

    update_project(
        project_id,
        status="ready",
        stage="Ready to download",
        progress=100,
        output_path=str(output_path.resolve()),
        error=None,
    )
    return {"project_id": project_id, "status": "ready"}


@celery_app.task(name="storyforge.scheduler_tick")
def scheduler_tick() -> dict[str, int]:
    dispatched = 0
    failed = 0
    for schedule in claim_due_schedules():
        schedule_id = schedule["id"]
        project_id = schedule["project_id"]
        try:
            project = get_project(project_id)
            if project is None:
                raise KeyError(f"Unknown project: {project_id}")
            if project["status"] in {"queued", "generating", "cancelling"}:
                raise RuntimeError("Project is already running.")
            if project["status"] == "ready":
                raise RuntimeError("Project is already complete.")
            reset_for_generation(project_id)
            result = generate_project.delay(project_id)
            update_schedule(
                schedule_id,
                status="triggered",
                task_id=result.id,
                error=None,
            )
            dispatched += 1
        except Exception as exc:
            update_schedule(
                schedule_id,
                status="failed",
                error=str(exc)[:500],
            )
            failed += 1
    return {"dispatched": dispatched, "failed": failed}
