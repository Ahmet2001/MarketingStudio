import { projectModes } from "./data";
import type {
  AiModel,
  AiProvider,
  AiProviderId,
  AppConnection,
  CreateProjectOptions,
  ProjectMode,
  ProjectModeId,
  ScheduledProject,
  VideoProject,
  Workflow,
  WorkflowRun,
} from "./types";

interface ApiProject {
  id: string;
  mode_id: ProjectModeId;
  mode: string;
  topic: string;
  title: string;
  language: string;
  duration: number;
  scenes: number;
  format: string;
  status:
    | "draft"
    | "queued"
    | "generating"
    | "cancelling"
    | "ready"
    | "failed"
    | "cancelled";
  stage: string;
  progress: number;
  error: string | null;
  output_url: string | null;
  created_at: string;
  updated_at: string;
}

interface ProjectListResponse {
  items: ApiProject[];
  total: number;
}

interface ApiSchedule {
  id: string;
  project_id: string;
  project_title: string;
  project_mode: string;
  run_at: string;
  timezone: string;
  status: "scheduled" | "dispatching" | "triggered" | "cancelled" | "failed";
  error: string | null;
}

interface ScheduleListResponse {
  items: ApiSchedule[];
  total: number;
}

interface ApiConnection {
  provider: AppConnection["provider"];
  name: string;
  description: string;
  status: AppConnection["status"];
  available: boolean;
  availability_note: string;
  account_label: string | null;
  scopes: string[];
  connected_at: string | null;
}

interface ApiWorkflow {
  id: string;
  name: string;
  nodes: Workflow["nodes"];
  edges: Workflow["edges"];
  status: Workflow["status"];
  last_run_at: string | null;
  last_run_status: Workflow["lastRunStatus"] | null;
  created_at: string;
  updated_at: string;
}

interface WorkflowListResponse {
  items: ApiWorkflow[];
  total: number;
}

interface ApiWorkflowRun {
  id: string;
  workflow_id: string;
  status: WorkflowRun["status"];
  project_id: string | null;
  schedule_id: string | null;
  destination: string | null;
  error: string | null;
  created_at: string;
}

interface ApiAiProvider {
  provider: AiProviderId;
  name: string;
  description: string;
  configured: boolean;
  key_hint: string | null;
  updated_at: string | null;
}

interface ApiAiModel {
  id: string;
  name: string;
  provider: AiProviderId;
  model_identifier: string;
  configuration: Record<string, unknown>;
  enabled: boolean;
  is_default: boolean;
  built_in: boolean;
  created_at: string;
  updated_at: string;
}

interface AiModelListResponse {
  items: ApiAiModel[];
  total: number;
}

const STATUS_LABELS: Record<ApiProject["status"], VideoProject["status"]> = {
  draft: "Draft",
  queued: "Queued",
  generating: "Generating",
  cancelling: "Cancelling",
  ready: "Ready",
  failed: "Failed",
  cancelled: "Cancelled",
};

const modeById = new Map<ProjectModeId, ProjectMode>(
  projectModes.map((mode) => [mode.id, mode]),
);

function formatDate(value: string): string {
  const date = new Date(value);
  const now = new Date();
  const isToday = date.toDateString() === now.toDateString();
  return isToday
    ? `Today, ${date.toLocaleTimeString([], {
        hour: "2-digit",
        minute: "2-digit",
      })}`
    : date.toLocaleDateString([], { month: "short", day: "numeric" });
}

function toVideoProject(project: ApiProject): VideoProject {
  const mode = modeById.get(project.mode_id);
  return {
    id: project.id,
    title: project.title,
    modeId: project.mode_id,
    mode: project.mode,
    date: formatDate(project.updated_at),
    duration: `00:${String(project.duration).padStart(2, "0")}`,
    status: STATUS_LABELS[project.status],
    stage: project.stage,
    progress: project.progress,
    accent: mode?.accent ?? "coral",
    outputUrl: project.output_url ?? undefined,
    error: project.error ?? undefined,
  };
}

function toSchedule(schedule: ApiSchedule): ScheduledProject {
  return {
    id: schedule.id,
    projectId: schedule.project_id,
    projectTitle: schedule.project_title,
    projectMode: schedule.project_mode,
    runAt: schedule.run_at,
    timezone: schedule.timezone,
    status: `${schedule.status[0].toUpperCase()}${schedule.status.slice(
      1,
    )}` as ScheduledProject["status"],
    error: schedule.error ?? undefined,
  };
}

function toConnection(connection: ApiConnection): AppConnection {
  return {
    provider: connection.provider,
    name: connection.name,
    description: connection.description,
    status: connection.status,
    available: connection.available,
    availabilityNote: connection.availability_note,
    accountLabel: connection.account_label ?? undefined,
    scopes: connection.scopes,
    connectedAt: connection.connected_at ?? undefined,
  };
}

function toWorkflow(workflow: ApiWorkflow): Workflow {
  return {
    id: workflow.id,
    name: workflow.name,
    nodes: workflow.nodes,
    edges: workflow.edges,
    status: workflow.status,
    lastRunAt: workflow.last_run_at ?? undefined,
    lastRunStatus: workflow.last_run_status ?? undefined,
    createdAt: workflow.created_at,
    updatedAt: workflow.updated_at,
  };
}

function toWorkflowRun(run: ApiWorkflowRun): WorkflowRun {
  return {
    id: run.id,
    workflowId: run.workflow_id,
    status: run.status,
    projectId: run.project_id ?? undefined,
    scheduleId: run.schedule_id ?? undefined,
    destination: run.destination ?? undefined,
    error: run.error ?? undefined,
    createdAt: run.created_at,
  };
}

function toAiProvider(provider: ApiAiProvider): AiProvider {
  return {
    provider: provider.provider,
    name: provider.name,
    description: provider.description,
    configured: provider.configured,
    keyHint: provider.key_hint ?? undefined,
    updatedAt: provider.updated_at ?? undefined,
  };
}

function toAiModel(model: ApiAiModel): AiModel {
  return {
    id: model.id,
    name: model.name,
    provider: model.provider,
    modelIdentifier: model.model_identifier,
    configuration: model.configuration,
    enabled: model.enabled,
    isDefault: model.is_default,
    builtIn: model.built_in,
    createdAt: model.created_at,
    updatedAt: model.updated_at,
  };
}

async function request<T>(
  path: string,
  options?: RequestInit,
): Promise<T> {
  const response = await fetch(path, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
  });
  if (!response.ok) {
    const body = (await response.json().catch(() => null)) as {
      detail?: string;
    } | null;
    throw new Error(body?.detail ?? `Request failed (${response.status}).`);
  }
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

export async function listProjects(
  signal?: AbortSignal,
): Promise<VideoProject[]> {
  const response = await request<ProjectListResponse>("/api/projects", { signal });
  return response.items.map(toVideoProject);
}

export async function createProject(
  modeId: ProjectModeId,
  options: CreateProjectOptions,
): Promise<VideoProject> {
  const project = await request<ApiProject>("/api/projects", {
    method: "POST",
    body: JSON.stringify({
      mode_id: modeId,
      topic: options.topic,
      language: options.language,
      duration: options.duration,
      scenes: options.scenes,
      format: "9:16",
      settings: {
        niche: options.settings.niche,
        skip_research: options.settings.skipResearch,
        research_region: options.settings.researchRegion,
        speaking_style: options.settings.speakingStyle,
        speech_speed: options.settings.speechSpeed,
        character_style: options.settings.characterStyle,
        real_photo_min_match: options.settings.realPhotoMinMatch,
        ai_model_id: options.settings.aiModelId,
      },
    }),
  });
  return toVideoProject(project);
}

export async function getLuckyPrompt(
  modeId: ProjectModeId,
  language: string,
  niche: string,
): Promise<{ prompt: string; source: "ai" | "fallback" }> {
  return request("/api/prompts/lucky", {
    method: "POST",
    body: JSON.stringify({
      mode_id: modeId,
      language,
      niche,
    }),
  });
}

export async function startProject(projectId: string): Promise<VideoProject> {
  const project = await request<ApiProject>(
    `/api/projects/${projectId}/generate`,
    { method: "POST" },
  );
  return toVideoProject(project);
}

export async function cancelProject(projectId: string): Promise<VideoProject> {
  const project = await request<ApiProject>(
    `/api/projects/${projectId}/cancel`,
    { method: "POST" },
  );
  return toVideoProject(project);
}

export async function retryProject(projectId: string): Promise<VideoProject> {
  const project = await request<ApiProject>(
    `/api/projects/${projectId}/retry`,
    { method: "POST" },
  );
  return toVideoProject(project);
}

export async function listSchedules(
  signal?: AbortSignal,
): Promise<ScheduledProject[]> {
  const response = await request<ScheduleListResponse>("/api/schedules", {
    signal,
  });
  return response.items.map(toSchedule);
}

export async function createSchedule(
  projectId: string,
  runAt: string,
): Promise<ScheduledProject> {
  const schedule = await request<ApiSchedule>("/api/schedules", {
    method: "POST",
    body: JSON.stringify({
      project_id: projectId,
      run_at: runAt,
      timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
    }),
  });
  return toSchedule(schedule);
}

export async function cancelSchedule(
  scheduleId: string,
): Promise<ScheduledProject> {
  const schedule = await request<ApiSchedule>(`/api/schedules/${scheduleId}`, {
    method: "DELETE",
  });
  return toSchedule(schedule);
}

export async function runScheduleNow(
  scheduleId: string,
): Promise<ScheduledProject> {
  const schedule = await request<ApiSchedule>(
    `/api/schedules/${scheduleId}/run-now`,
    { method: "POST" },
  );
  return toSchedule(schedule);
}

export async function listConnections(
  signal?: AbortSignal,
): Promise<AppConnection[]> {
  const connections = await request<ApiConnection[]>("/api/connections", {
    signal,
  });
  return connections.map(toConnection);
}

export async function connectApp(
  provider: AppConnection["provider"],
): Promise<{ connection?: AppConnection; authorizationUrl?: string }> {
  const response = await request<{
    connection: ApiConnection | null;
    authorization_url: string | null;
  }>(`/api/connections/${provider}/connect`, { method: "POST" });
  return {
    connection: response.connection
      ? toConnection(response.connection)
      : undefined,
    authorizationUrl: response.authorization_url ?? undefined,
  };
}

export async function disconnectApp(
  provider: AppConnection["provider"],
): Promise<AppConnection> {
  const response = await request<ApiConnection>(
    `/api/connections/${provider}`,
    { method: "DELETE" },
  );
  return toConnection(response);
}

export async function listAiProviders(
  signal?: AbortSignal,
): Promise<AiProvider[]> {
  const providers = await request<ApiAiProvider[]>("/api/ai/providers", {
    signal,
  });
  return providers.map(toAiProvider);
}

export async function saveAiProviderKey(
  provider: AiProviderId,
  apiKey: string,
): Promise<AiProvider> {
  const response = await request<ApiAiProvider>(`/api/ai/providers/${provider}`, {
    method: "PUT",
    body: JSON.stringify({ api_key: apiKey }),
  });
  return toAiProvider(response);
}

export async function removeAiProviderKey(
  provider: AiProviderId,
): Promise<AiProvider> {
  const response = await request<ApiAiProvider>(`/api/ai/providers/${provider}`, {
    method: "DELETE",
  });
  return toAiProvider(response);
}

export async function listAiModels(signal?: AbortSignal): Promise<AiModel[]> {
  const response = await request<AiModelListResponse>("/api/ai/models", {
    signal,
  });
  return response.items.map(toAiModel);
}

export async function saveAiModel(model: AiModel): Promise<AiModel> {
  const path = model.id ? `/api/ai/models/${model.id}` : "/api/ai/models";
  const response = await request<ApiAiModel>(path, {
    method: model.id ? "PUT" : "POST",
    body: JSON.stringify({
      name: model.name,
      provider: model.provider,
      model_identifier: model.modelIdentifier,
      configuration: model.configuration,
      enabled: model.enabled,
      is_default: model.isDefault,
    }),
  });
  return toAiModel(response);
}

export async function deleteAiModel(modelId: string): Promise<void> {
  await request<void>(`/api/ai/models/${modelId}`, { method: "DELETE" });
}

export async function listWorkflows(
  signal?: AbortSignal,
): Promise<Workflow[]> {
  const response = await request<WorkflowListResponse>("/api/workflows", {
    signal,
  });
  return response.items.map(toWorkflow);
}

export async function saveWorkflow(workflow: Workflow): Promise<Workflow> {
  const path = workflow.id ? `/api/workflows/${workflow.id}` : "/api/workflows";
  const response = await request<ApiWorkflow>(path, {
    method: workflow.id ? "PUT" : "POST",
    body: JSON.stringify({
      name: workflow.name,
      nodes: workflow.nodes,
      edges: workflow.edges,
      status: workflow.status,
    }),
  });
  return toWorkflow(response);
}

export async function runWorkflow(workflowId: string): Promise<WorkflowRun> {
  const response = await request<ApiWorkflowRun>(
    `/api/workflows/${workflowId}/run`,
    { method: "POST" },
  );
  return toWorkflowRun(response);
}
