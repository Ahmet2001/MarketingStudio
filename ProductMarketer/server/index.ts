import { randomUUID } from 'node:crypto'
import { mkdir } from 'node:fs/promises'
import { resolve } from 'node:path'
import cors from 'cors'
import express, { type NextFunction, type Request, type Response } from 'express'
import multer from 'multer'
import { z } from 'zod'
import { toolById, toolCatalog } from './catalog'
import { decryptCredential, encryptCredential } from './credential-vault'
import { all, db, DEMO_USER_ID, get } from './db'
import { enqueueGeneration, processGeneration } from './generation-engine'
import { providerById, providerCatalog, testProviderConnection } from './model-providers'

const port = Number(process.env.API_PORT ?? 8787)
const storageRoot = resolve(process.env.STORAGE_PATH ?? 'storage')
const uploadsDirectory = resolve(storageRoot, 'uploads')
await mkdir(uploadsDirectory, { recursive: true })

const upload = multer({
  storage: multer.diskStorage({
    destination: uploadsDirectory,
    filename: (_request, file, callback) => {
      const safeExtension = file.originalname.toLowerCase().match(/\.(png|jpe?g|webp)$/)?.[0] ?? '.bin'
      callback(null, `${randomUUID()}${safeExtension}`)
    },
  }),
  limits: { fileSize: 20 * 1024 * 1024 },
  fileFilter: (_request, file, callback) => {
    callback(null, ['image/png', 'image/jpeg', 'image/webp'].includes(file.mimetype))
  },
})

const app = express()
app.disable('x-powered-by')
app.use(cors({ origin: true, credentials: false }))
app.use(express.json({ limit: '1mb' }))
app.use('/media', express.static(storageRoot, { fallthrough: false, maxAge: '1h' }))

const profileSchema = z.object({
  firstName: z.string().trim().min(1).max(80),
  lastName: z.string().trim().min(1).max(80),
  email: z.string().email(),
  jobTitle: z.string().trim().max(120),
  timezone: z.string().trim().max(80),
  bio: z.string().trim().max(500),
})

const settingsSchema = z.object({
  aiGeneration: z.boolean(),
  backgroundRemoval: z.boolean(),
  generationNotifications: z.boolean(),
  experimentalStyles: z.boolean(),
})

const generationSchema = z.object({
  toolId: z.string().min(1),
  title: z.string().trim().min(1).max(160).optional(),
  choice: z.string().trim().min(1).max(160),
  prompt: z.string().trim().max(1000).default(''),
  uploadId: z.string().uuid().nullable().optional(),
})

const providerModelsSchema = z.object({
  llm: z.string().trim().max(200).default(''),
  vlm: z.string().trim().max(200).default(''),
  image: z.string().trim().max(200).default(''),
  video: z.string().trim().max(200).default(''),
})

const providerConfigSchema = z.object({
  label: z.string().trim().min(1).max(100),
  baseUrl: z.string().trim().url().refine((value) => {
    const url = new URL(value)
    return ['http:', 'https:'].includes(url.protocol) && !url.username && !url.password
  }, 'Base URL must be an HTTP(S) URL without embedded credentials'),
  apiKey: z.string().trim().max(1000).optional(),
  enabled: z.boolean().default(true),
  models: providerModelsSchema,
})

const modelRouteSchema = z.object({
  llm: z.object({ provider: z.string().min(1), model: z.string().trim().min(1).max(200) }).nullable(),
  vlm: z.object({ provider: z.string().min(1), model: z.string().trim().min(1).max(200) }).nullable(),
  image: z.object({ provider: z.string().min(1), model: z.string().trim().min(1).max(200) }).nullable(),
  video: z.object({ provider: z.string().min(1), model: z.string().trim().min(1).max(200) }).nullable(),
})

function projectResponse(row: Record<string, unknown>) {
  return {
    id: row.id,
    title: row.title,
    toolId: row.tool_id,
    category: row.category,
    status: row.status,
    choice: row.choice,
    prompt: row.prompt,
    uploadId: row.upload_id,
    outputCount: Number(row.output_count ?? 0),
    createdAt: row.created_at,
    updatedAt: row.updated_at,
  }
}

function generationResponse(generationId: string) {
  const row = get<Record<string, unknown>>('SELECT * FROM generations WHERE id = ? AND user_id = ?', generationId, DEMO_USER_ID)
  if (!row) return undefined
  const outputs = all<Record<string, unknown>>('SELECT * FROM outputs WHERE generation_id = ? ORDER BY position', generationId)
  const scenes = all<Record<string, unknown>>('SELECT * FROM scenes WHERE generation_id = ? ORDER BY position', generationId)
  return {
    id: row.id,
    projectId: row.project_id,
    parentGenerationId: row.parent_generation_id,
    provider: row.provider,
    model: row.model,
    status: row.status,
    prompt: row.prompt,
    input: JSON.parse(String(row.input_json)),
    usage: row.usage_json ? JSON.parse(String(row.usage_json)) : null,
    estimatedCostCents: row.estimated_cost_cents,
    error: row.error,
    createdAt: row.created_at,
    completedAt: row.completed_at,
    outputs: outputs.map((output) => ({
      id: output.id,
      position: output.position,
      kind: output.kind,
      url: output.url,
      thumbnailUrl: output.thumbnail_url,
      metadata: JSON.parse(String(output.metadata_json)),
      status: output.status,
      approved: Boolean(output.approved),
    })),
    scenes: scenes.map((scene) => ({
      id: scene.id,
      position: scene.position,
      title: scene.title,
      script: scene.script,
      status: scene.status,
      outputId: scene.output_id,
    })),
  }
}

function providerConfigResponse(row: Record<string, unknown>) {
  return {
    provider: row.provider,
    label: row.label,
    baseUrl: row.base_url,
    hasApiKey: Boolean(row.api_key_encrypted),
    models: JSON.parse(String(row.models_json)),
    enabled: Boolean(row.enabled),
    status: row.status,
    lastTestedAt: row.last_tested_at,
    lastError: row.last_error,
    updatedAt: row.updated_at,
  }
}

function modelRoutesResponse() {
  const row = get<Record<string, unknown>>('SELECT * FROM model_routes WHERE user_id = ?', DEMO_USER_ID)
  const route = (capability: 'llm' | 'vlm' | 'image' | 'video') => {
    const provider = row?.[`${capability}_provider`]
    const model = row?.[`${capability}_model`]
    return provider && model ? { provider, model } : null
  }
  return {
    llm: route('llm'),
    vlm: route('vlm'),
    image: route('image'),
    video: route('video'),
    updatedAt: row?.updated_at,
  }
}

app.get('/api/health', (_request, response) => {
  const pending = get<{ count: number }>("SELECT COUNT(*) AS count FROM generations WHERE status IN ('pending', 'processing')")
  response.json({ status: 'ok', database: 'sqlite', provider: 'local', pendingJobs: pending?.count ?? 0, timestamp: new Date().toISOString() })
})

app.get('/api/catalog', (_request, response) => response.json({ tools: toolCatalog }))

app.get('/api/me', (_request, response) => {
  const user = get<Record<string, unknown>>('SELECT * FROM users WHERE id = ?', DEMO_USER_ID)
  response.json({
    id: user?.id,
    firstName: user?.first_name,
    lastName: user?.last_name,
    email: user?.email,
    jobTitle: user?.job_title,
    timezone: user?.timezone,
    bio: user?.bio,
  })
})

app.patch('/api/me', (request, response) => {
  const profile = profileSchema.parse(request.body)
  db.prepare(`
    UPDATE users SET first_name = ?, last_name = ?, email = ?, job_title = ?, timezone = ?, bio = ? WHERE id = ?
  `).run(profile.firstName, profile.lastName, profile.email, profile.jobTitle, profile.timezone, profile.bio, DEMO_USER_ID)
  response.json({ profile })
})

app.get('/api/settings', (_request, response) => {
  const row = get<Record<string, unknown>>('SELECT * FROM settings WHERE user_id = ?', DEMO_USER_ID)
  response.json({
    aiGeneration: Boolean(row?.ai_generation),
    backgroundRemoval: Boolean(row?.background_removal),
    generationNotifications: Boolean(row?.generation_notifications),
    experimentalStyles: Boolean(row?.experimental_styles),
  })
})

app.patch('/api/settings', (request, response) => {
  const settings = settingsSchema.parse(request.body)
  db.prepare(`
    UPDATE settings SET ai_generation = ?, background_removal = ?, generation_notifications = ?, experimental_styles = ?, updated_at = ?
    WHERE user_id = ?
  `).run(
    Number(settings.aiGeneration),
    Number(settings.backgroundRemoval),
    Number(settings.generationNotifications),
    Number(settings.experimentalStyles),
    new Date().toISOString(),
    DEMO_USER_ID,
  )
  response.json({ settings })
})

app.get('/api/model-providers', (_request, response) => {
  const configRows = all<Record<string, unknown>>(
    'SELECT * FROM model_providers WHERE user_id = ? ORDER BY provider',
    DEMO_USER_ID,
  )
  const configByProvider = new Map(configRows.map((row) => [String(row.provider), providerConfigResponse(row)]))
  response.json({
    providers: providerCatalog.map((provider) => ({
      id: provider.id,
      label: provider.label,
      description: provider.description,
      capabilities: provider.capabilities,
      defaultBaseUrl: provider.defaultBaseUrl,
      requiresApiKey: provider.requiresApiKey,
      config: configByProvider.get(provider.id) ?? null,
    })),
    routes: modelRoutesResponse(),
  })
})

app.put('/api/model-providers/:provider', (request, response) => {
  const definition = providerById.get(request.params.provider)
  if (!definition) return response.status(404).json({ error: 'Unknown model provider' })
  const input = providerConfigSchema.parse(request.body)
  const existing = get<Record<string, unknown>>(
    'SELECT * FROM model_providers WHERE user_id = ? AND provider = ?',
    DEMO_USER_ID,
    definition.id,
  )
  if (definition.requiresApiKey && !input.apiKey && !existing?.api_key_encrypted) {
    return response.status(400).json({ error: `${definition.label} requires an API key` })
  }

  const encrypted = input.apiKey ? encryptCredential(input.apiKey) : null
  const id = existing?.id ? String(existing.id) : randomUUID()
  const timestamp = new Date().toISOString()
  db.prepare(`
    INSERT INTO model_providers (
      id, user_id, provider, label, base_url, api_key_encrypted, api_key_iv, api_key_tag,
      models_json, enabled, status, last_tested_at, last_error, created_at, updated_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'untested', NULL, NULL, ?, ?)
    ON CONFLICT(user_id, provider) DO UPDATE SET
      label = excluded.label,
      base_url = excluded.base_url,
      api_key_encrypted = COALESCE(excluded.api_key_encrypted, model_providers.api_key_encrypted),
      api_key_iv = COALESCE(excluded.api_key_iv, model_providers.api_key_iv),
      api_key_tag = COALESCE(excluded.api_key_tag, model_providers.api_key_tag),
      models_json = excluded.models_json,
      enabled = excluded.enabled,
      status = 'untested',
      last_error = NULL,
      updated_at = excluded.updated_at
  `).run(
    id,
    DEMO_USER_ID,
    definition.id,
    input.label,
    input.baseUrl.replace(/\/+$/, ''),
    encrypted?.ciphertext ?? null,
    encrypted?.iv ?? null,
    encrypted?.tag ?? null,
    JSON.stringify(input.models),
    Number(input.enabled),
    existing?.created_at ? String(existing.created_at) : timestamp,
    timestamp,
  )
  const saved = get<Record<string, unknown>>('SELECT * FROM model_providers WHERE id = ?', id)
  response.json({ config: saved ? providerConfigResponse(saved) : null })
})

app.post('/api/model-providers/:provider/test', async (request, response, next) => {
  try {
    const definition = providerById.get(request.params.provider)
    if (!definition) return response.status(404).json({ error: 'Unknown model provider' })
    const row = get<Record<string, unknown>>(
      'SELECT * FROM model_providers WHERE user_id = ? AND provider = ?',
      DEMO_USER_ID,
      definition.id,
    )
    if (!row) return response.status(404).json({ error: 'Configure this provider before testing it' })
    const apiKey = row.api_key_encrypted
      ? decryptCredential({
          ciphertext: String(row.api_key_encrypted),
          iv: String(row.api_key_iv),
          tag: String(row.api_key_tag),
        })
      : undefined
    const result = await testProviderConnection(definition, String(row.base_url), apiKey)
    const timestamp = new Date().toISOString()
    db.prepare(`
      UPDATE model_providers SET status = ?, last_tested_at = ?, last_error = ?, updated_at = ? WHERE id = ?
    `).run(result.ok ? 'connected' : 'error', timestamp, result.ok ? null : result.message, timestamp, row.id as string)
    response.json({ result, config: providerConfigResponse({
      ...row,
      status: result.ok ? 'connected' : 'error',
      last_tested_at: timestamp,
      last_error: result.ok ? null : result.message,
      updated_at: timestamp,
    }) })
  } catch (error) {
    next(error)
  }
})

app.delete('/api/model-providers/:provider', (request, response) => {
  const definition = providerById.get(request.params.provider)
  if (!definition) return response.status(404).json({ error: 'Unknown model provider' })
  db.exec('BEGIN')
  try {
    db.prepare('DELETE FROM model_providers WHERE user_id = ? AND provider = ?').run(DEMO_USER_ID, definition.id)
    for (const capability of ['llm', 'vlm', 'image', 'video'] as const) {
      db.prepare(`
        UPDATE model_routes
        SET ${capability}_provider = CASE WHEN ${capability}_provider = ? THEN NULL ELSE ${capability}_provider END,
            ${capability}_model = CASE WHEN ${capability}_provider = ? THEN NULL ELSE ${capability}_model END,
            updated_at = ?
        WHERE user_id = ?
      `).run(definition.id, definition.id, new Date().toISOString(), DEMO_USER_ID)
    }
    db.exec('COMMIT')
  } catch (error) {
    db.exec('ROLLBACK')
    throw error
  }
  response.status(204).end()
})

app.get('/api/model-routes', (_request, response) => {
  response.json({ routes: modelRoutesResponse() })
})

app.put('/api/model-routes', (request, response) => {
  const routes = modelRouteSchema.parse(request.body)
  for (const [capability, route] of Object.entries(routes)) {
    if (!route) continue
    const config = get<Record<string, unknown>>(
      'SELECT enabled, models_json FROM model_providers WHERE user_id = ? AND provider = ?',
      DEMO_USER_ID,
      route.provider,
    )
    if (!config || !config.enabled) {
      return response.status(400).json({ error: `Configure and enable ${route.provider} before assigning the ${capability.toUpperCase()} route` })
    }
    const definition = providerById.get(route.provider)
    if (!definition?.capabilities.includes(capability as 'llm' | 'vlm' | 'image' | 'video')) {
      return response.status(400).json({ error: `${definition?.label ?? route.provider} does not support the ${capability} capability` })
    }
  }
  const timestamp = new Date().toISOString()
  db.prepare(`
    UPDATE model_routes SET
      llm_provider = ?, llm_model = ?, vlm_provider = ?, vlm_model = ?,
      image_provider = ?, image_model = ?, video_provider = ?, video_model = ?, updated_at = ?
    WHERE user_id = ?
  `).run(
    routes.llm?.provider ?? null,
    routes.llm?.model ?? null,
    routes.vlm?.provider ?? null,
    routes.vlm?.model ?? null,
    routes.image?.provider ?? null,
    routes.image?.model ?? null,
    routes.video?.provider ?? null,
    routes.video?.model ?? null,
    timestamp,
    DEMO_USER_ID,
  )
  response.json({ routes: modelRoutesResponse() })
})

app.get('/api/projects', (request, response) => {
  const category = typeof request.query.category === 'string' ? request.query.category : undefined
  const rows = category
    ? all<Record<string, unknown>>(`
        SELECT p.*, (SELECT COUNT(*) FROM generations g JOIN outputs o ON o.generation_id = g.id WHERE g.project_id = p.id) AS output_count
        FROM projects p WHERE p.user_id = ? AND p.category = ? ORDER BY p.updated_at DESC
      `, DEMO_USER_ID, category)
    : all<Record<string, unknown>>(`
        SELECT p.*, (SELECT COUNT(*) FROM generations g JOIN outputs o ON o.generation_id = g.id WHERE g.project_id = p.id) AS output_count
        FROM projects p WHERE p.user_id = ? ORDER BY p.updated_at DESC
      `, DEMO_USER_ID)
  response.json({ projects: rows.map(projectResponse) })
})

app.get('/api/projects/:id', (request, response) => {
  const project = get<Record<string, unknown>>('SELECT * FROM projects WHERE id = ? AND user_id = ?', request.params.id, DEMO_USER_ID)
  if (!project) return response.status(404).json({ error: 'Project not found' })
  const generations = all<{ id: string }>('SELECT id FROM generations WHERE project_id = ? ORDER BY created_at DESC', request.params.id)
  response.json({ project: projectResponse(project), generations: generations.map(({ id }) => generationResponse(id)) })
})

app.post('/api/uploads', upload.single('file'), (request, response) => {
  if (!request.file) return response.status(400).json({ error: 'A PNG, JPG, or WEBP product image is required' })
  const id = randomUUID()
  const createdAt = new Date().toISOString()
  const url = `/media/uploads/${request.file.filename}`
  db.prepare(`
    INSERT INTO uploads (id, user_id, original_name, stored_name, mime_type, size_bytes, url, created_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
  `).run(id, DEMO_USER_ID, request.file.originalname, request.file.filename, request.file.mimetype, request.file.size, url, createdAt)
  response.status(201).json({ upload: { id, name: request.file.originalname, mimeType: request.file.mimetype, size: request.file.size, url, createdAt } })
})

app.post('/api/generations', (request, response) => {
  const input = generationSchema.parse(request.body)
  const tool = toolById.get(input.toolId)
  if (!tool) return response.status(400).json({ error: 'Unknown creation tool' })
  if (input.uploadId) {
    const uploadRecord = get('SELECT id FROM uploads WHERE id = ? AND user_id = ?', input.uploadId, DEMO_USER_ID)
    if (!uploadRecord) return response.status(400).json({ error: 'Upload not found' })
  }
  const projectId = randomUUID()
  const generationId = randomUUID()
  const createdAt = new Date().toISOString()
  const title = input.title ?? `${tool.title} · ${new Date().toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}`

  db.exec('BEGIN')
  try {
    db.prepare(`
      INSERT INTO projects (id, user_id, title, tool_id, category, status, choice, prompt, upload_id, created_at, updated_at)
      VALUES (?, ?, ?, ?, ?, 'generating', ?, ?, ?, ?, ?)
    `).run(projectId, DEMO_USER_ID, title, tool.id, tool.category, input.choice, input.prompt, input.uploadId ?? null, createdAt, createdAt)
    db.prepare(`
      INSERT INTO generations (
        id, project_id, user_id, parent_generation_id, provider, model, status, prompt, input_json,
        usage_json, estimated_cost_cents, error, created_at, completed_at
      ) VALUES (?, ?, ?, NULL, ?, ?, 'pending', ?, ?, NULL, ?, NULL, ?, NULL)
    `).run(generationId, projectId, DEMO_USER_ID, tool.provider, tool.model, input.prompt, JSON.stringify(input), tool.estimatedCostCents, createdAt)
    db.exec('COMMIT')
  } catch (error) {
    db.exec('ROLLBACK')
    throw error
  }
  enqueueGeneration(generationId)
  response.status(202).json({ generation: generationResponse(generationId), pollUrl: `/api/generations/${generationId}` })
})

app.get('/api/generations', (_request, response) => {
  const generations = all<{ id: string }>('SELECT id FROM generations WHERE user_id = ? ORDER BY created_at DESC LIMIT 100', DEMO_USER_ID)
  response.json({ generations: generations.map(({ id }) => generationResponse(id)) })
})

app.get('/api/generations/:id', (request, response) => {
  const generation = generationResponse(request.params.id)
  if (!generation) return response.status(404).json({ error: 'Generation not found' })
  response.json({ generation })
})

app.post('/api/generations/:id/revisions', (request, response) => {
  const changeRequest = z.object({ changeRequest: z.string().trim().min(2).max(1000) }).parse(request.body).changeRequest
  const parent = get<Record<string, unknown>>('SELECT * FROM generations WHERE id = ? AND user_id = ?', request.params.id, DEMO_USER_ID)
  if (!parent) return response.status(404).json({ error: 'Generation not found' })
  const project = get<Record<string, unknown>>('SELECT * FROM projects WHERE id = ?', String(parent.project_id))
  if (!project) return response.status(404).json({ error: 'Project not found' })
  const tool = toolById.get(String(project.tool_id))
  if (!tool) return response.status(400).json({ error: 'Unknown creation tool' })
  const id = randomUUID()
  const createdAt = new Date().toISOString()
  const prompt = [String(parent.prompt), `Revision request: ${changeRequest}`].filter(Boolean).join('\\n')
  db.prepare(`
    INSERT INTO generations (
      id, project_id, user_id, parent_generation_id, provider, model, status, prompt, input_json,
      usage_json, estimated_cost_cents, error, created_at, completed_at
    ) VALUES (?, ?, ?, ?, ?, ?, 'pending', ?, ?, NULL, ?, NULL, ?, NULL)
  `).run(id, String(parent.project_id), DEMO_USER_ID, String(parent.id), tool.provider, tool.model, prompt, JSON.stringify({ changeRequest }), tool.estimatedCostCents, createdAt)
  db.prepare("UPDATE projects SET status = 'generating', updated_at = ? WHERE id = ?").run(createdAt, String(parent.project_id))
  enqueueGeneration(id)
  response.status(202).json({ generation: generationResponse(id), pollUrl: `/api/generations/${id}` })
})

app.post('/api/generations/:id/approve', (request, response) => {
  const body = z.object({ outputId: z.string().uuid().optional() }).parse(request.body ?? {})
  const generation = get<Record<string, unknown>>('SELECT * FROM generations WHERE id = ? AND user_id = ?', request.params.id, DEMO_USER_ID)
  if (!generation) return response.status(404).json({ error: 'Generation not found' })
  const output = body.outputId
    ? get<Record<string, unknown>>('SELECT * FROM outputs WHERE id = ? AND generation_id = ?', body.outputId, request.params.id)
    : get<Record<string, unknown>>('SELECT * FROM outputs WHERE generation_id = ? ORDER BY position LIMIT 1', request.params.id)
  if (!output) return response.status(400).json({ error: 'No generated output is available to approve' })
  db.exec('BEGIN')
  try {
    db.prepare('UPDATE outputs SET approved = 0 WHERE generation_id = ?').run(request.params.id)
    db.prepare("UPDATE outputs SET approved = 1, status = 'approved' WHERE id = ?").run(output.id as string)
    db.prepare("UPDATE scenes SET status = 'approved' WHERE generation_id = ?").run(request.params.id)
    db.prepare("UPDATE projects SET status = 'ready', updated_at = ? WHERE id = ?").run(new Date().toISOString(), generation.project_id as string)
    db.exec('COMMIT')
  } catch (error) {
    db.exec('ROLLBACK')
    throw error
  }
  response.json({ generation: generationResponse(request.params.id) })
})

app.patch('/api/scenes/:id', (request, response) => {
  const sceneInput = z.object({ script: z.string().trim().min(1).max(1000).optional(), status: z.enum(['ready', 'approved', 'revision_requested']).optional() }).parse(request.body)
  const scene = get<Record<string, unknown>>(`
    SELECT s.* FROM scenes s JOIN generations g ON g.id = s.generation_id WHERE s.id = ? AND g.user_id = ?
  `, request.params.id, DEMO_USER_ID)
  if (!scene) return response.status(404).json({ error: 'Scene not found' })
  db.prepare('UPDATE scenes SET script = ?, status = ? WHERE id = ?')
    .run(sceneInput.script ?? String(scene.script), sceneInput.status ?? String(scene.status), request.params.id)
  response.json({ scene: { ...scene, script: sceneInput.script ?? scene.script, status: sceneInput.status ?? scene.status } })
})

app.get('/api/videos', (_request, response) => {
  const rows = all<Record<string, unknown>>(`
    SELECT p.*,
      (SELECT o.url FROM generations g JOIN outputs o ON o.generation_id = g.id
       WHERE g.project_id = p.id ORDER BY g.created_at DESC, o.position ASC LIMIT 1) AS thumbnail_url,
      (SELECT g.id FROM generations g WHERE g.project_id = p.id ORDER BY g.created_at DESC LIMIT 1) AS generation_id
    FROM projects p WHERE p.user_id = ? AND p.category = 'video' ORDER BY p.updated_at DESC
  `, DEMO_USER_ID)
  response.json({
    videos: rows.map((row) => ({
      id: row.id,
      generationId: row.generation_id,
      title: row.title,
      type: toolById.get(String(row.tool_id))?.title ?? row.tool_id,
      status: row.status,
      duration: '00:24',
      thumbnailUrl: row.thumbnail_url,
      updatedAt: row.updated_at,
    })),
  })
})

app.use((error: unknown, _request: Request, response: Response, _next: NextFunction) => {
  void _next
  if (error instanceof z.ZodError) {
    response.status(400).json({ error: 'Invalid request', details: error.issues })
    return
  }
  if (error instanceof multer.MulterError) {
    response.status(400).json({ error: error.message })
    return
  }
  const message = error instanceof Error ? error.message : 'Internal server error'
  console.error(error)
  response.status(500).json({ error: message })
})

const pending = all<{ id: string }>("SELECT id FROM generations WHERE status IN ('pending', 'processing')")
pending.forEach(({ id }) => void processGeneration(id))

app.listen(port, '127.0.0.1', () => {
  console.log(`ProductMarketer API listening on http://127.0.0.1:${port}`)
})
