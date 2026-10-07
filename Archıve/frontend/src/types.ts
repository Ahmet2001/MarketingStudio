import type { LucideIcon } from "lucide-react";

export type ViewId =
  | "create"
  | "videos"
  | "workflows"
  | "scheduler"
  | "connections"
  | "ai-models"
  | "profile"
  | "settings";

export type ProjectModeId =
  | "ai-photos"
  | "reddit"
  | "real-images"
  | "documentary"
  | "stock-explainer"
  | "avatar";

export interface ProjectMode {
  id: ProjectModeId;
  title: string;
  description: string;
  engine: string;
  available: boolean;
  badge?: string;
  accent: "coral" | "lime" | "blue" | "gold" | "violet" | "mint";
  Icon: LucideIcon;
  promptPlaceholder: string;
  examples: string[];
}

export interface VideoProject {
  id: string;
  title: string;
  modeId: ProjectModeId;
  mode: string;
  date: string;
  duration: string;
  status:
    | "Ready"
    | "Queued"
    | "Generating"
    | "Cancelling"
    | "Draft"
    | "Failed"
    | "Cancelled";
  stage: string;
  progress?: number;
  accent: ProjectMode["accent"];
  outputUrl?: string;
  error?: string;
}

export interface CreateProjectOptions {
  topic: string;
  duration: number;
  language: string;
  scenes: number;
  settings: {
    niche: string;
    skipResearch: boolean;
    researchRegion: string;
    speakingStyle: "mysterious" | "excited" | "sad" | "angry" | "serious";
    speechSpeed: number | null;
    characterStyle:
      | "auto"
      | "life-sim"
      | "animal"
      | "horror"
      | "animated-human";
    realPhotoMinMatch: number;
    aiModelId: string | null;
  };
}

export type AiProviderId = "replicate" | "fal" | "together" | "gemini";

export interface AiProvider {
  provider: AiProviderId;
  name: string;
  description: string;
  configured: boolean;
  keyHint?: string;
  updatedAt?: string;
}

export interface AiModel {
  id?: string;
  name: string;
  provider: AiProviderId;
  modelIdentifier: string;
  configuration: Record<string, unknown>;
  enabled: boolean;
  isDefault: boolean;
  builtIn?: boolean;
  createdAt?: string;
  updatedAt?: string;
}

export interface ScheduledProject {
  id: string;
  projectId: string;
  projectTitle: string;
  projectMode: string;
  runAt: string;
  timezone: string;
  status: "Scheduled" | "Dispatching" | "Triggered" | "Cancelled" | "Failed";
  error?: string;
}

export interface AppConnection {
  provider: "youtube" | "tiktok" | "instagram";
  name: string;
  description: string;
  status: "connected" | "disconnected";
  available: boolean;
  availabilityNote: string;
  accountLabel?: string;
  scopes: string[];
  connectedAt?: string;
}

export type WorkflowNodeKind =
  | "content-generator"
  | "scheduler"
  | "app-connection";

export interface WorkflowNode {
  id: string;
  kind: WorkflowNodeKind;
  subtype: string;
  label: string;
  x: number;
  y: number;
  config: {
    topic?: string;
    duration?: number;
    scenes?: number;
    language?: string;
    niche?: string;
    skip_research?: boolean;
    delay_minutes?: number;
    timezone?: string;
  };
}

export interface WorkflowEdge {
  id: string;
  source: string;
  target: string;
}

export interface Workflow {
  id?: string;
  name: string;
  nodes: WorkflowNode[];
  edges: WorkflowEdge[];
  status: "draft" | "active" | "paused";
  lastRunAt?: string;
  lastRunStatus?: "queued" | "scheduled" | "failed";
  createdAt?: string;
  updatedAt?: string;
}

export interface WorkflowRun {
  id: string;
  workflowId: string;
  status: "queued" | "scheduled" | "failed";
  projectId?: string;
  scheduleId?: string;
  destination?: string;
  error?: string;
  createdAt: string;
}
