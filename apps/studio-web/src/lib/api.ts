export interface UploadRecord {
  id: string
  name: string
  mimeType: string
  size: number
  url: string
  createdAt: string
}

export interface GenerationOutput {
  id: string
  position: number
  kind: 'image' | 'video' | 'carousel'
  url: string
  thumbnailUrl: string
  metadata: {
    width: number
    height: number
    durationSeconds: number | null
  }
  status: string
  approved: boolean
}

export interface GenerationScene {
  id: string
  position: number
  title: string
  script: string
  status: string
  outputId: string | null
}

export interface GenerationRecord {
  id: string
  projectId: string
  parentGenerationId: string | null
  provider: string
  model: string
  status: 'pending' | 'processing' | 'complete' | 'error'
  prompt: string
  estimatedCostCents: number
  error: string | null
  outputs: GenerationOutput[]
  scenes: GenerationScene[]
}

export interface VideoRecord {
  id: string
  generationId: string | null
  title: string
  type: string
  status: string
  duration: string
  thumbnailUrl: string | null
  updatedAt: string
}

export interface ProjectRecord {
  id: string
  title: string
  toolId: string
  category: 'image' | 'video' | 'social'
  status: string
  choice: string
  prompt: string
  uploadId: string | null
  outputCount: number
  createdAt: string
  updatedAt: string
}

export interface ProfileRecord {
  firstName: string
  lastName: string
  email: string
  jobTitle: string
  timezone: string
  bio: string
}

export interface SettingsRecord {
  aiGeneration: boolean
  backgroundRemoval: boolean
  generationNotifications: boolean
  experimentalStyles: boolean
}

export type ModelCapability = 'llm' | 'vlm' | 'image' | 'video'

export interface ProviderModels {
  llm: string
  vlm: string
  image: string
  video: string
}

export interface ModelProviderConfig {
  provider: string
  label: string
  baseUrl: string
  hasApiKey: boolean
  models: ProviderModels
  enabled: boolean
  status: 'untested' | 'connected' | 'error'
  lastTestedAt: string | null
  lastError: string | null
  updatedAt: string
}

export interface ModelProvider {
  id: string
  label: string
  description: string
  capabilities: ModelCapability[]
  defaultBaseUrl: string
  requiresApiKey: boolean
  config: ModelProviderConfig | null
}

export type ModelRoute = { provider: string; model: string } | null

export interface ModelRoutes {
  llm: ModelRoute
  vlm: ModelRoute
  image: ModelRoute
  video: ModelRoute
  updatedAt?: string
}

export interface ModelProviderBundle {
  providers: ModelProvider[]
  routes: ModelRoutes
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, init)
  if (response.status === 204) return undefined as T
  const body = await response.json() as T & { error?: string }
  if (!response.ok) throw new Error(body.error ?? `Request failed with status ${response.status}`)
  return body
}

export async function uploadProduct(file: File): Promise<UploadRecord> {
  const form = new FormData()
  form.append('file', file)
  const body = await request<{ upload: UploadRecord }>('/api/uploads', { method: 'POST', body: form })
  return body.upload
}

export async function createGeneration(input: {
  toolId: string
  title: string
  choice: string
  prompt: string
  uploadId: string
}): Promise<GenerationRecord> {
  const body = await request<{ generation: GenerationRecord }>('/api/generations', {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify(input),
  })
  return body.generation
}

export async function getGeneration(id: string): Promise<GenerationRecord> {
  const body = await request<{ generation: GenerationRecord }>(`/api/generations/${id}`)
  return body.generation
}

export async function waitForGeneration(id: string): Promise<GenerationRecord> {
  for (let attempt = 0; attempt < 150; attempt += 1) {
    const generation = await getGeneration(id)
    if (generation.status === 'complete') return generation
    if (generation.status === 'error') throw new Error(generation.error ?? 'Generation failed')
    await new Promise((resolve) => window.setTimeout(resolve, 400))
  }
  throw new Error('Generation is taking longer than expected. It is still saved in your projects.')
}

export async function reviseGeneration(id: string, changeRequest: string): Promise<GenerationRecord> {
  const body = await request<{ generation: GenerationRecord }>(`/api/generations/${id}/revisions`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ changeRequest }),
  })
  return body.generation
}

export async function approveGeneration(id: string, outputId: string): Promise<GenerationRecord> {
  const body = await request<{ generation: GenerationRecord }>(`/api/generations/${id}/approve`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ outputId }),
  })
  return body.generation
}

export async function getVideos(): Promise<VideoRecord[]> {
  const body = await request<{ videos: VideoRecord[] }>('/api/videos')
  return body.videos
}

export async function getProjects(): Promise<ProjectRecord[]> {
  const body = await request<{ projects: ProjectRecord[] }>('/api/projects')
  return body.projects
}

export async function getProfile(): Promise<ProfileRecord> {
  return request<ProfileRecord>('/api/me')
}

export async function saveProfile(profile: ProfileRecord): Promise<void> {
  await request('/api/me', {
    method: 'PATCH',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify(profile),
  })
}

export async function getSettings(): Promise<SettingsRecord> {
  return request<SettingsRecord>('/api/settings')
}

export async function saveSettings(settings: SettingsRecord): Promise<void> {
  await request('/api/settings', {
    method: 'PATCH',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify(settings),
  })
}

export async function getModelProviders(): Promise<ModelProviderBundle> {
  return request<ModelProviderBundle>('/api/model-providers')
}

export async function saveModelProvider(provider: string, input: {
  label: string
  baseUrl: string
  apiKey?: string
  enabled: boolean
  models: ProviderModels
}): Promise<ModelProviderConfig> {
  const body = await request<{ config: ModelProviderConfig }>(`/api/model-providers/${provider}`, {
    method: 'PUT',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify(input),
  })
  return body.config
}

export async function testModelProvider(provider: string): Promise<{
  ok: boolean
  latencyMs: number
  message: string
  modelCount?: number
}> {
  const body = await request<{ result: { ok: boolean; latencyMs: number; message: string; modelCount?: number } }>(
    `/api/model-providers/${provider}/test`,
    { method: 'POST' },
  )
  return body.result
}

export async function removeModelProvider(provider: string): Promise<void> {
  await request(`/api/model-providers/${provider}`, { method: 'DELETE' })
}

export async function saveModelRoutes(routes: Omit<ModelRoutes, 'updatedAt'>): Promise<ModelRoutes> {
  const body = await request<{ routes: ModelRoutes }>('/api/model-routes', {
    method: 'PUT',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify(routes),
  })
  return body.routes
}
