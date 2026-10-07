from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path

from celery.exceptions import CeleryError
from fastapi import FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse

from .config import (
    ALLOWED_ORIGINS,
    FRONTEND_URL,
    MOCK_CONNECTIONS,
    MOCK_GENERATION,
    PROJECTS_ROOT,
    TASKS_EAGER,
)
from .ai_providers import (
    delete_api_key,
    get_api_key,
    list_ai_providers,
    provider_response,
    require_ai_provider,
    save_api_key,
)
from .connectors import (
    build_authorization_url,
    complete_oauth,
    connect_mock,
    connection_response,
    disconnect_provider,
    list_connections,
    require_provider,
)
from .modes import MODES
from .models import (
    AiModelCreate,
    AiModelListResponse,
    AiModelResponse,
    AiModelUpdate,
    AiProviderCredentialUpdate,
    AiProviderResponse,
    ConnectionResponse,
    ConnectionStartResponse,
    HealthResponse,
    LuckyPromptRequest,
    LuckyPromptResponse,
    ProjectCreate,
    ProjectListResponse,
    ProjectLogsResponse,
    ProjectResponse,
    ScheduleCreate,
    ScheduleListResponse,
    ScheduleResponse,
    WorkflowCreate,
    WorkflowListResponse,
    WorkflowResponse,
    WorkflowRunResponse,
    WorkflowUpdate,
)
from .prompt_ideas import create_lucky_prompt
from .repository import (
    create_ai_model,
    create_project,
    create_schedule,
    create_workflow,
    delete_ai_model,
    get_ai_model,
    get_connection,
    get_project,
    get_project_output_path,
    get_schedule,
    get_workflow,
    initialize_database,
    list_ai_models,
    list_projects,
    list_schedules,
    list_workflows,
    read_project_logs,
    record_workflow_run,
    reset_for_generation,
    update_ai_model,
    update_project,
    update_schedule,
    update_workflow,
)
from .tasks import generate_project, scheduler_tick


@asynccontextmanager
async def lifespan(_: FastAPI):
    initialize_database()
    yield


app = FastAPI(
    title="Storyforge API",
    version="0.1.0",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def require_project(project_id: str) -> dict:
    project = get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found.")
    return project


def enqueue_project(project_id: str) -> dict:
    reset_for_generation(project_id)
    try:
        result = generate_project.delay(project_id)
    except (CeleryError, ConnectionError, OSError) as exc:
        update_project(
            project_id,
            status="failed",
            stage="Queue unavailable",
            error="The generation queue is unavailable. Start Redis and the worker.",
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Generation queue unavailable.",
        ) from exc
    project = require_project(project_id)
    if project["task_id"] is None:
        project = update_project(project_id, task_id=result.id)
    return project


@app.get("/api/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        queue_mode="eager" if TASKS_EAGER else "celery",
        generation_mode="mock" if MOCK_GENERATION else "real",
    )


@app.get("/api/ai/providers", response_model=list[AiProviderResponse])
def ai_providers() -> list[dict]:
    return list_ai_providers()


@app.put(
    "/api/ai/providers/{provider_id}",
    response_model=AiProviderResponse,
)
def update_ai_provider(
    provider_id: str,
    payload: AiProviderCredentialUpdate,
) -> dict:
    try:
        provider = require_ai_provider(provider_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="AI provider not found.") from exc
    save_api_key(provider.id, payload.api_key)
    return provider_response(provider)


@app.delete(
    "/api/ai/providers/{provider_id}",
    response_model=AiProviderResponse,
)
def remove_ai_provider(provider_id: str) -> dict:
    try:
        return delete_api_key(provider_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="AI provider not found.") from exc


@app.get("/api/ai/models", response_model=AiModelListResponse)
def ai_models() -> AiModelListResponse:
    items = list_ai_models()
    return AiModelListResponse(items=items, total=len(items))


@app.post(
    "/api/ai/models",
    response_model=AiModelResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_ai_model_record(payload: AiModelCreate) -> dict:
    return create_ai_model(**payload.model_dump())


@app.put(
    "/api/ai/models/{model_id}",
    response_model=AiModelResponse,
)
def update_ai_model_record(model_id: str, payload: AiModelUpdate) -> dict:
    if get_ai_model(model_id) is None:
        raise HTTPException(status_code=404, detail="AI model not found.")
    return update_ai_model(model_id, **payload.model_dump())


@app.delete("/api/ai/models/{model_id}")
def delete_ai_model_record(model_id: str) -> dict:
    try:
        delete_ai_model(model_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="AI model not found.") from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {"deleted": True}


@app.get("/api/modes")
def modes() -> list[dict]:
    return [mode.__dict__ for mode in MODES.values()]


@app.post("/api/prompts/lucky", response_model=LuckyPromptResponse)
async def lucky_prompt(payload: LuckyPromptRequest) -> LuckyPromptResponse:
    prompt, source = await create_lucky_prompt(
        mode_id=payload.mode_id,
        language=payload.language,
        niche=payload.niche,
    )
    return LuckyPromptResponse(prompt=prompt, source=source)


def require_workflow(workflow_id: str) -> dict:
    workflow = get_workflow(workflow_id)
    if workflow is None:
        raise HTTPException(status_code=404, detail="Workflow not found.")
    return workflow


@app.get("/api/workflows", response_model=WorkflowListResponse)
def workflows() -> WorkflowListResponse:
    items = list_workflows()
    return WorkflowListResponse(items=items, total=len(items))


@app.post(
    "/api/workflows",
    response_model=WorkflowResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_workflow_record(payload: WorkflowCreate) -> dict:
    return create_workflow(
        name=payload.name,
        nodes=[node.model_dump() for node in payload.nodes],
        edges=[edge.model_dump() for edge in payload.edges],
        status=payload.status,
    )


@app.put("/api/workflows/{workflow_id}", response_model=WorkflowResponse)
def update_workflow_record(
    workflow_id: str,
    payload: WorkflowUpdate,
) -> dict:
    require_workflow(workflow_id)
    return update_workflow(
        workflow_id,
        name=payload.name,
        nodes=[node.model_dump() for node in payload.nodes],
        edges=[edge.model_dump() for edge in payload.edges],
        status=payload.status,
    )


def _reachable_workflow_nodes(
    generator_id: str,
    nodes_by_id: dict[str, dict],
    edges: list[dict],
) -> list[dict]:
    targets: dict[str, list[str]] = {}
    for edge in edges:
        if edge["source"] not in nodes_by_id or edge["target"] not in nodes_by_id:
            raise HTTPException(
                status_code=422,
                detail="Every connection must reference an existing node.",
            )
        targets.setdefault(edge["source"], []).append(edge["target"])
    reachable: list[dict] = []
    pending = [generator_id]
    visited: set[str] = set()
    while pending:
        node_id = pending.pop(0)
        if node_id in visited:
            continue
        visited.add(node_id)
        reachable.append(nodes_by_id[node_id])
        pending.extend(targets.get(node_id, []))
    return reachable


@app.post(
    "/api/workflows/{workflow_id}/run",
    response_model=WorkflowRunResponse,
)
async def run_workflow(workflow_id: str) -> dict:
    workflow = require_workflow(workflow_id)
    nodes = workflow["nodes"]
    nodes_by_id = {node["id"]: node for node in nodes}
    if len(nodes_by_id) != len(nodes):
        raise HTTPException(status_code=422, detail="Workflow node IDs must be unique.")
    generators = [
        node for node in nodes if node["kind"] == "content-generator"
    ]
    if len(generators) != 1:
        raise HTTPException(
            status_code=422,
            detail="A workflow needs exactly one content generator.",
        )
    generator = generators[0]
    reachable = _reachable_workflow_nodes(
        generator["id"],
        nodes_by_id,
        workflow["edges"],
    )
    schedulers = [node for node in reachable if node["kind"] == "scheduler"]
    destinations = [
        node for node in reachable if node["kind"] == "app-connection"
    ]
    if len(schedulers) > 1 or len(destinations) > 1:
        raise HTTPException(
            status_code=422,
            detail="Use at most one scheduler and one destination in a workflow path.",
        )

    mode_id = generator["subtype"]
    mode = MODES.get(mode_id)
    if mode is None or not mode.available:
        raise HTTPException(
            status_code=422,
            detail="The selected content generator is not available yet.",
        )

    destination = destinations[0]["subtype"] if destinations else None
    if destination:
        connection_value = get_connection(destination)
        if not connection_value or connection_value["status"] != "connected":
            raise HTTPException(
                status_code=409,
                detail=f"Connect {destinations[0]['label']} before running this workflow.",
            )

    config = generator.get("config") or {}
    language = str(config.get("language") or "English")
    niche = str(config.get("niche") or "general-storytelling")
    topic = str(config.get("topic") or "").strip()
    if not topic:
        topic, _ = await create_lucky_prompt(
            mode_id=mode_id,
            language=language,
            niche=niche,
        )
    project_value = create_project(
        ProjectCreate(
            mode_id=mode_id,
            topic=topic,
            language=language,
            duration=int(config.get("duration") or 45),
            scenes=int(config.get("scenes") or 7),
            settings={
                "niche": niche,
                "skip_research": bool(config.get("skip_research", False)),
            },
        )
    )

    schedule_value = None
    run_status = "queued"
    if schedulers:
        schedule_config = schedulers[0].get("config") or {}
        delay_minutes = max(
            1,
            min(10_080, int(schedule_config.get("delay_minutes") or 5)),
        )
        schedule_value = create_schedule(
            project_value["id"],
            datetime.now(UTC) + timedelta(minutes=delay_minutes),
            str(schedule_config.get("timezone") or "UTC"),
        )
        run_status = "scheduled"
    else:
        enqueue_project(project_value["id"])

    return record_workflow_run(
        workflow_id,
        status=run_status,
        project_id=project_value["id"],
        schedule_id=schedule_value["id"] if schedule_value else None,
        destination=destination,
    )


@app.post(
    "/api/projects",
    response_model=ProjectResponse,
    status_code=status.HTTP_201_CREATED,
)
def create(payload: ProjectCreate) -> dict:
    mode = MODES[payload.mode_id]
    if not mode.available:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"{mode.name} does not have a generation worker yet.",
        )
    model_id = payload.settings.ai_model_id
    if model_id:
        model = get_ai_model(model_id)
        if model is None or not model["enabled"]:
            raise HTTPException(
                status_code=422,
                detail="The selected AI model is unavailable.",
            )
        payload = payload.model_copy(
            update={
                "settings": payload.settings.model_copy(
                    update={
                        "ai_provider": model["provider"],
                        "ai_model_identifier": model["model_identifier"],
                        "ai_model_config": model["configuration"],
                    }
                )
            }
        )
    return create_project(payload)


@app.get("/api/projects", response_model=ProjectListResponse)
def projects() -> ProjectListResponse:
    items = list_projects()
    return ProjectListResponse(items=items, total=len(items))


@app.get("/api/projects/{project_id}", response_model=ProjectResponse)
def project(project_id: str) -> dict:
    return require_project(project_id)


@app.post("/api/projects/{project_id}/generate", response_model=ProjectResponse)
def start_generation(project_id: str) -> dict:
    project_data = require_project(project_id)
    if project_data["status"] in {"queued", "generating", "cancelling"}:
        raise HTTPException(status_code=409, detail="Project is already running.")
    if not MODES[project_data["mode_id"]].available:
        raise HTTPException(status_code=422, detail="Mode is not available.")
    ai_provider = project_data["settings"].get("ai_provider")
    if (
        project_data["mode_id"] == "ai-photos"
        and ai_provider
        and not MOCK_GENERATION
        and get_api_key(ai_provider) is None
    ):
        raise HTTPException(
            status_code=409,
            detail=f"Add your {require_ai_provider(ai_provider).name} API key before generating.",
        )
    return enqueue_project(project_id)


@app.post("/api/projects/{project_id}/retry", response_model=ProjectResponse)
def retry_generation(project_id: str) -> dict:
    project_data = require_project(project_id)
    if project_data["status"] not in {"failed", "cancelled"}:
        raise HTTPException(
            status_code=409,
            detail="Only failed or cancelled projects can be retried.",
        )
    ai_provider = project_data["settings"].get("ai_provider")
    if (
        project_data["mode_id"] == "ai-photos"
        and ai_provider
        and not MOCK_GENERATION
        and get_api_key(ai_provider) is None
    ):
        raise HTTPException(
            status_code=409,
            detail=f"Add your {require_ai_provider(ai_provider).name} API key before retrying.",
        )
    return enqueue_project(project_id)


@app.post("/api/projects/{project_id}/cancel", response_model=ProjectResponse)
def cancel_generation(project_id: str) -> dict:
    project_data = require_project(project_id)
    if project_data["status"] not in {"queued", "generating"}:
        raise HTTPException(status_code=409, detail="Project is not running.")
    return update_project(
        project_id,
        status="cancelling",
        stage="Stopping safely",
        cancel_requested=1,
    )


@app.get("/api/projects/{project_id}/logs", response_model=ProjectLogsResponse)
def project_logs(
    project_id: str,
    limit: int = Query(default=200, ge=1, le=1000),
) -> ProjectLogsResponse:
    require_project(project_id)
    return ProjectLogsResponse(
        project_id=project_id,
        lines=read_project_logs(project_id, limit),
    )


def require_schedule(schedule_id: str) -> dict:
    schedule_value = get_schedule(schedule_id)
    if schedule_value is None:
        raise HTTPException(status_code=404, detail="Schedule not found.")
    return schedule_value


@app.get("/api/schedules", response_model=ScheduleListResponse)
def schedules() -> ScheduleListResponse:
    items = list_schedules()
    return ScheduleListResponse(items=items, total=len(items))


@app.post(
    "/api/schedules",
    response_model=ScheduleResponse,
    status_code=status.HTTP_201_CREATED,
)
def schedule_project(payload: ScheduleCreate) -> dict:
    project_data = require_project(payload.project_id)
    if project_data["status"] not in {"draft", "failed", "cancelled"}:
        raise HTTPException(
            status_code=409,
            detail="Only draft, failed, or cancelled projects can be scheduled.",
        )
    run_at = payload.run_at.astimezone(UTC)
    if run_at <= datetime.now(UTC):
        raise HTTPException(
            status_code=422,
            detail="Schedule time must be in the future.",
        )
    return create_schedule(payload.project_id, run_at, payload.timezone)


@app.post(
    "/api/schedules/{schedule_id}/run-now",
    response_model=ScheduleResponse,
)
def run_schedule_now(schedule_id: str) -> dict:
    schedule_value = require_schedule(schedule_id)
    if schedule_value["status"] != "scheduled":
        raise HTTPException(status_code=409, detail="Schedule is not active.")
    update_schedule(schedule_id, run_at=datetime.now(UTC).isoformat())
    try:
        scheduler_tick.delay()
    except (CeleryError, ConnectionError, OSError) as exc:
        raise HTTPException(
            status_code=503,
            detail="Scheduler queue unavailable.",
        ) from exc
    return require_schedule(schedule_id)


@app.delete(
    "/api/schedules/{schedule_id}",
    response_model=ScheduleResponse,
)
def cancel_schedule(schedule_id: str) -> dict:
    schedule_value = require_schedule(schedule_id)
    if schedule_value["status"] != "scheduled":
        raise HTTPException(status_code=409, detail="Schedule is not active.")
    return update_schedule(schedule_id, status="cancelled")


@app.get("/api/connections", response_model=list[ConnectionResponse])
def connections() -> list[dict]:
    return list_connections()


@app.post(
    "/api/connections/{provider_id}/connect",
    response_model=ConnectionStartResponse,
)
def connect(provider_id: str) -> ConnectionStartResponse:
    try:
        provider = require_provider(provider_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Provider not found.") from exc
    if not provider.available:
        raise HTTPException(status_code=503, detail=provider.availability_note)
    if MOCK_CONNECTIONS:
        return ConnectionStartResponse(
            connection=ConnectionResponse.model_validate(connect_mock(provider))
        )
    return ConnectionStartResponse(
        authorization_url=build_authorization_url(provider)
    )


@app.get(
    "/api/connections/{provider_id}/callback",
    response_class=HTMLResponse,
)
async def connection_callback(
    provider_id: str,
    code: str = "",
    state_value: str = Query(default="", alias="state"),
    error: str = "",
) -> HTMLResponse:
    try:
        provider = require_provider(provider_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Provider not found.") from exc
    if error:
        message = f"{provider.name} connection was declined."
    elif not code or not state_value:
        message = "The connection callback was incomplete."
    else:
        try:
            await complete_oauth(provider, code, state_value)
            message = f"{provider.name} connected successfully."
        except (ValueError, RuntimeError) as exc:
            message = str(exc)
    safe_message = (
        message.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    )
    return HTMLResponse(
        f"""
        <!doctype html>
        <html lang="en">
          <head><meta charset="utf-8"><title>Storyforge connection</title></head>
          <body style="font-family:system-ui;padding:40px;background:#f6f5f1">
            <h1>{safe_message}</h1>
            <p>You can close this window and return to Storyforge.</p>
            <script>
              if (window.opener) {{
                window.opener.postMessage(
                  {{ type: "storyforge:connection", provider: "{provider.id}" }},
                  "{FRONTEND_URL}"
                );
                window.close();
              }}
            </script>
          </body>
        </html>
        """
    )


@app.delete(
    "/api/connections/{provider_id}",
    response_model=ConnectionResponse,
)
def disconnect(provider_id: str) -> dict:
    try:
        provider = require_provider(provider_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Provider not found.") from exc
    return disconnect_provider(provider)


@app.get("/api/projects/{project_id}/download")
def download_project(project_id: str) -> FileResponse:
    require_project(project_id)
    output_path = get_project_output_path(project_id)
    if output_path is None or not output_path.is_file():
        raise HTTPException(status_code=404, detail="Final video is not available.")
    expected_root = (PROJECTS_ROOT / project_id).resolve()
    try:
        output_path.relative_to(expected_root)
    except ValueError as exc:
        raise HTTPException(status_code=403, detail="Invalid output path.") from exc
    return FileResponse(
        path=Path(output_path),
        media_type="video/mp4",
        filename=output_path.name,
    )
    delete_ai_model,
    get_ai_model,
    list_ai_models,
    update_ai_model,
