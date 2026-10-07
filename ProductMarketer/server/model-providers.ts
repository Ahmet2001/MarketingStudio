export type ModelCapability = 'llm' | 'vlm' | 'image' | 'video'

export interface ProviderDefinition {
  id: string
  label: string
  description: string
  capabilities: ModelCapability[]
  defaultBaseUrl: string
  requiresApiKey: boolean
  auth: 'bearer' | 'x-api-key' | 'google-query' | 'fal-key' | 'none'
  testPath: string
}

export const providerCatalog: ProviderDefinition[] = [
  {
    id: 'openai',
    label: 'OpenAI',
    description: 'Text, vision, image, and video models through the OpenAI API.',
    capabilities: ['llm', 'vlm', 'image', 'video'],
    defaultBaseUrl: 'https://api.openai.com/v1',
    requiresApiKey: true,
    auth: 'bearer',
    testPath: '/models',
  },
  {
    id: 'anthropic',
    label: 'Anthropic',
    description: 'Claude language and vision-language models.',
    capabilities: ['llm', 'vlm'],
    defaultBaseUrl: 'https://api.anthropic.com/v1',
    requiresApiKey: true,
    auth: 'x-api-key',
    testPath: '/models',
  },
  {
    id: 'gemini',
    label: 'Google Gemini',
    description: 'Google multimodal, image, and video model APIs.',
    capabilities: ['llm', 'vlm', 'image', 'video'],
    defaultBaseUrl: 'https://generativelanguage.googleapis.com/v1beta',
    requiresApiKey: true,
    auth: 'google-query',
    testPath: '/models',
  },
  {
    id: 'replicate',
    label: 'Replicate',
    description: 'Hosted image and video models with versioned predictions.',
    capabilities: ['image', 'video'],
    defaultBaseUrl: 'https://api.replicate.com/v1',
    requiresApiKey: true,
    auth: 'bearer',
    testPath: '/account',
  },
  {
    id: 'fal',
    label: 'fal',
    description: 'Fast serverless image and video inference endpoints.',
    capabilities: ['image', 'video'],
    defaultBaseUrl: 'https://api.fal.ai/v1',
    requiresApiKey: true,
    auth: 'fal-key',
    testPath: '/models?limit=1',
  },
  {
    id: 'huggingface',
    label: 'Hugging Face',
    description: 'Inference Providers for language, vision, and image models.',
    capabilities: ['llm', 'vlm', 'image'],
    defaultBaseUrl: 'https://router.huggingface.co/v1',
    requiresApiKey: true,
    auth: 'bearer',
    testPath: '/models',
  },
  {
    id: 'ollama',
    label: 'Ollama',
    description: 'Run local language and vision models without an API key.',
    capabilities: ['llm', 'vlm'],
    defaultBaseUrl: 'http://127.0.0.1:11434',
    requiresApiKey: false,
    auth: 'none',
    testPath: '/api/tags',
  },
  {
    id: 'custom',
    label: 'OpenAI-compatible',
    description: 'Connect any OpenAI-compatible gateway or self-hosted endpoint.',
    capabilities: ['llm', 'vlm', 'image', 'video'],
    defaultBaseUrl: '',
    requiresApiKey: false,
    auth: 'bearer',
    testPath: '/models',
  },
]

export const providerById = new Map(providerCatalog.map((provider) => [provider.id, provider]))

function joinUrl(baseUrl: string, path: string): URL {
  return new URL(`${baseUrl.replace(/\/+$/, '')}${path.startsWith('/') ? path : `/${path}`}`)
}

export async function testProviderConnection(
  provider: ProviderDefinition,
  baseUrl: string,
  apiKey: string | undefined,
): Promise<{ ok: boolean; latencyMs: number; message: string; modelCount?: number }> {
  const url = joinUrl(baseUrl, provider.testPath)
  const headers = new Headers({ accept: 'application/json' })
  if (provider.auth === 'bearer' && apiKey) headers.set('authorization', `Bearer ${apiKey}`)
  if (provider.auth === 'x-api-key' && apiKey) {
    headers.set('x-api-key', apiKey)
    headers.set('anthropic-version', '2023-06-01')
  }
  if (provider.auth === 'fal-key' && apiKey) headers.set('authorization', `Key ${apiKey}`)
  if (provider.auth === 'google-query' && apiKey) url.searchParams.set('key', apiKey)

  const controller = new AbortController()
  const timeout = setTimeout(() => controller.abort(), 10_000)
  const startedAt = performance.now()
  try {
    const response = await fetch(url, { headers, signal: controller.signal })
    const latencyMs = Math.round(performance.now() - startedAt)
    if (!response.ok) {
      const detail = await response.text()
      return {
        ok: false,
        latencyMs,
        message: `Provider returned ${response.status}${detail ? `: ${detail.slice(0, 180)}` : ''}`,
      }
    }
    const body = await response.json() as Record<string, unknown>
    const models = Array.isArray(body.data)
      ? body.data
      : Array.isArray(body.models)
        ? body.models
        : Array.isArray(body.results)
          ? body.results
          : undefined
    return {
      ok: true,
      latencyMs,
      message: `Connected in ${latencyMs} ms`,
      modelCount: models?.length,
    }
  } catch (error) {
    const latencyMs = Math.round(performance.now() - startedAt)
    const message = error instanceof Error && error.name === 'AbortError'
      ? 'Connection timed out after 10 seconds'
      : error instanceof Error
        ? error.message
        : 'Connection failed'
    return { ok: false, latencyMs, message }
  } finally {
    clearTimeout(timeout)
  }
}
