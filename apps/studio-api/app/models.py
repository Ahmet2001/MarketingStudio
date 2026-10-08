from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


ProjectModeId = Literal[
    "ai-photos",
    "reddit",
    "real-images",
    "documentary",
    "stock-explainer",
    "avatar",
]
ProjectStatus = Literal[
    "draft",
    "queued",
    "generating",
    "cancelling",
    "ready",
    "failed",
    "cancelled",
]


class GenerationSettings(BaseModel):
    niche: str = Field(default="general-storytelling", max_length=100)
    skip_research: bool = False
    research_region: str = Field(default="us-en", pattern=r"^[a-z]{2}-[a-z]{2}$")
    speaking_style: Literal[
        "mysterious", "excited", "sad", "angry", "serious"
    ] = "serious"
    speech_speed: float | None = Field(default=None, ge=0.7, le=1.2)
    character_style: Literal[
        "auto", "life-sim", "animal", "horror", "animated-human"
    ] = "auto"
    voice_id: str | None = Field(default=None, max_length=120)
    real_photo_min_match: int = Field(default=70, ge=0, le=100)
    ai_model_id: str | None = Field(default=None, max_length=64)
    ai_provider: Literal["replicate", "fal", "together", "gemini"] | None = None
    ai_model_identifier: str | None = Field(default=None, max_length=240)
    ai_model_config: dict[str, Any] = Field(default_factory=dict)


class ProjectCreate(BaseModel):
    mode_id: ProjectModeId
    topic: str = Field(min_length=3, max_length=500)
    language: str = Field(default="English", min_length=2, max_length=60)
    duration: int = Field(default=45, ge=10, le=180)
    scenes: int = Field(default=7, ge=2, le=20)
    format: Literal["9:16"] = "9:16"
    settings: GenerationSettings = Field(default_factory=GenerationSettings)

    @field_validator("topic")
    @classmethod
    def clean_topic(cls, value: str) -> str:
        return " ".join(value.split())


class ProjectResponse(BaseModel):
    id: str
    mode_id: ProjectModeId
    mode: str
    topic: str
    title: str
    language: str
    duration: int
    scenes: int
    format: str
    settings: dict[str, Any]
    status: ProjectStatus
    stage: str
    progress: int
    error: str | None
    task_id: str | None
    output_url: str | None
    created_at: datetime
    updated_at: datetime


class ProjectListResponse(BaseModel):
    items: list[ProjectResponse]
    total: int


class ProjectLogsResponse(BaseModel):
    project_id: str
    lines: list[str]


class HealthResponse(BaseModel):
    status: Literal["ok"]
    queue_mode: Literal["celery", "eager"]
    generation_mode: Literal["real", "mock"]


class LuckyPromptRequest(BaseModel):
    mode_id: ProjectModeId
    language: str = Field(default="English", min_length=2, max_length=60)
    niche: str = Field(default="general-storytelling", max_length=100)


class LuckyPromptResponse(BaseModel):
    prompt: str = Field(min_length=3, max_length=500)
    source: Literal["ai", "fallback"]


WorkflowNodeKind = Literal[
    "content-generator", "scheduler", "app-connection"
]
WorkflowStatus = Literal["draft", "active", "paused"]
WorkflowRunStatus = Literal["queued", "scheduled", "failed"]


class WorkflowNode(BaseModel):
    id: str = Field(min_length=1, max_length=80)
    kind: WorkflowNodeKind
    subtype: str = Field(min_length=1, max_length=80)
    capability_id: str | None = Field(
        default=None,
        max_length=120,
        pattern=r"^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)+$",
    )
    label: str = Field(min_length=1, max_length=120)
    x: float = Field(ge=0, le=4000)
    y: float = Field(ge=0, le=2500)
    config: dict[str, Any] = Field(default_factory=dict)


class WorkflowEdge(BaseModel):
    id: str = Field(min_length=1, max_length=120)
    source: str = Field(min_length=1, max_length=80)
    target: str = Field(min_length=1, max_length=80)

    @field_validator("target")
    @classmethod
    def prevent_self_reference(cls, value: str, info: Any) -> str:
        if info.data.get("source") == value:
            raise ValueError("A workflow node cannot connect to itself.")
        return value


class WorkflowCreate(BaseModel):
    name: str = Field(default="Untitled workflow", min_length=1, max_length=120)
    nodes: list[WorkflowNode] = Field(default_factory=list, max_length=40)
    edges: list[WorkflowEdge] = Field(default_factory=list, max_length=80)
    status: WorkflowStatus = "draft"


class WorkflowUpdate(WorkflowCreate):
    pass


class WorkflowResponse(WorkflowCreate):
    id: str
    last_run_at: datetime | None
    last_run_status: WorkflowRunStatus | None
    created_at: datetime
    updated_at: datetime


class WorkflowListResponse(BaseModel):
    items: list[WorkflowResponse]
    total: int


class WorkflowRunResponse(BaseModel):
    id: str
    workflow_id: str
    status: WorkflowRunStatus
    project_id: str | None
    schedule_id: str | None
    destination: str | None
    error: str | None
    created_at: datetime


ScheduleStatus = Literal[
    "scheduled", "dispatching", "triggered", "cancelled", "failed"
]


class ScheduleCreate(BaseModel):
    project_id: str = Field(min_length=8, max_length=64)
    run_at: datetime
    timezone: str = Field(default="UTC", min_length=3, max_length=80)

    @field_validator("run_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("run_at must include a timezone offset.")
        return value


class ScheduleResponse(BaseModel):
    id: str
    project_id: str
    project_title: str
    project_mode: str
    run_at: datetime
    timezone: str
    status: ScheduleStatus
    task_id: str | None
    error: str | None
    created_at: datetime
    updated_at: datetime


class ScheduleListResponse(BaseModel):
    items: list[ScheduleResponse]
    total: int


ConnectionStatus = Literal["connected", "disconnected"]


class ConnectionResponse(BaseModel):
    provider: Literal["youtube", "tiktok", "instagram"]
    name: str
    description: str
    status: ConnectionStatus
    available: bool
    availability_note: str
    account_label: str | None
    scopes: list[str]
    connected_at: datetime | None


class ConnectionStartResponse(BaseModel):
    connection: ConnectionResponse | None = None
    authorization_url: str | None = None


AiProviderId = Literal["replicate", "fal", "together", "gemini"]


class AiProviderCredentialUpdate(BaseModel):
    api_key: str = Field(min_length=8, max_length=500)

    @field_validator("api_key")
    @classmethod
    def clean_api_key(cls, value: str) -> str:
        cleaned = value.strip()
        if any(character.isspace() for character in cleaned):
            raise ValueError("API keys cannot contain whitespace.")
        return cleaned


class AiProviderResponse(BaseModel):
    provider: AiProviderId
    name: str
    description: str
    configured: bool
    key_hint: str | None
    updated_at: datetime | None


class AiModelCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    provider: AiProviderId
    model_identifier: str = Field(
        min_length=3,
        max_length=240,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9._:/-]+$",
    )
    configuration: dict[str, Any] = Field(default_factory=dict)
    enabled: bool = True
    is_default: bool = False

    @field_validator("name", "model_identifier")
    @classmethod
    def clean_model_text(cls, value: str) -> str:
        return value.strip()

    @field_validator("configuration")
    @classmethod
    def validate_configuration(cls, value: dict[str, Any]) -> dict[str, Any]:
        import json

        try:
            serialized = json.dumps(value, allow_nan=False)
        except (TypeError, ValueError) as exc:
            raise ValueError("Configuration must contain valid JSON values.") from exc
        if len(serialized) > 12_000:
            raise ValueError("Model configuration is too large.")
        if "prompt" in value:
            raise ValueError("The prompt is supplied by the video project.")
        return value


class AiModelUpdate(AiModelCreate):
    pass


class AiModelResponse(AiModelCreate):
    id: str
    built_in: bool
    created_at: datetime
    updated_at: datetime


class AiModelListResponse(BaseModel):
    items: list[AiModelResponse]
    total: int
