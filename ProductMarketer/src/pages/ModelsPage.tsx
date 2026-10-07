import { useEffect, useState } from 'react'
import {
  Bot,
  Check,
  ChevronDown,
  CircleAlert,
  Cpu,
  Eye,
  Film,
  Image,
  KeyRound,
  Link2,
  LoaderCircle,
  LockKeyhole,
  Network,
  PlugZap,
  Save,
  ShieldCheck,
  Trash2,
  X,
} from 'lucide-react'
import {
  getModelProviders,
  removeModelProvider,
  saveModelProvider,
  saveModelRoutes,
  testModelProvider,
  type ModelCapability,
  type ModelProvider,
  type ModelProviderBundle,
  type ModelRoutes,
  type ProviderModels,
} from '../lib/api'

const capabilityMeta: Record<ModelCapability, {
  label: string
  shortLabel: string
  description: string
  icon: typeof Bot
}> = {
  llm: {
    label: 'Language model',
    shortLabel: 'LLM',
    description: 'Copy, scripts, prompts, and campaign reasoning.',
    icon: Bot,
  },
  vlm: {
    label: 'Vision-language model',
    shortLabel: 'VLM',
    description: 'Understand product photos, layouts, and visual feedback.',
    icon: Eye,
  },
  image: {
    label: 'Image generator',
    shortLabel: 'IMAGE',
    description: 'Create and revise covers, scenes, and product photography.',
    icon: Image,
  },
  video: {
    label: 'Video generator',
    shortLabel: 'VIDEO',
    description: 'Generate motion, UGC scenes, and final clips.',
    icon: Film,
  },
}

const providerTones: Record<string, string> = {
  openai: 'green',
  anthropic: 'orange',
  gemini: 'blue',
  replicate: 'violet',
  fal: 'coral',
  huggingface: 'gold',
  ollama: 'slate',
  custom: 'prism',
}

const emptyModels: ProviderModels = { llm: '', vlm: '', image: '', video: '' }
const emptyRoutes: ModelRoutes = { llm: null, vlm: null, image: null, video: null }

interface ProviderForm {
  label: string
  baseUrl: string
  apiKey: string
  enabled: boolean
  models: ProviderModels
}

interface ModelsPageProps {
  onSaved: (message: string) => void
}

function createProviderForm(provider: ModelProvider): ProviderForm {
  return {
    label: provider.config?.label ?? provider.label,
    baseUrl: provider.config?.baseUrl ?? provider.defaultBaseUrl,
    apiKey: '',
    enabled: provider.config?.enabled ?? true,
    models: provider.config?.models ?? emptyModels,
  }
}

function ConnectionStatus({ provider }: { provider: ModelProvider }) {
  if (!provider.config) return <span className="provider-status not-configured">Not configured</span>
  if (provider.config.status === 'connected') {
    return <span className="provider-status connected"><Check size={11} /> Connected</span>
  }
  if (provider.config.status === 'error') {
    return <span className="provider-status error"><CircleAlert size={11} /> Check connection</span>
  }
  return <span className="provider-status untested">Ready to test</span>
}

export function ModelsPage({ onSaved }: ModelsPageProps) {
  const [bundle, setBundle] = useState<ModelProviderBundle | null>(null)
  const [routes, setRoutes] = useState<ModelRoutes>(emptyRoutes)
  const [selectedProviderId, setSelectedProviderId] = useState<string | null>(null)
  const [form, setForm] = useState<ProviderForm | null>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [testing, setTesting] = useState(false)
  const [testMessage, setTestMessage] = useState<{ ok: boolean; text: string } | null>(null)
  const [error, setError] = useState<string | null>(null)

  const load = async () => {
    const nextBundle = await getModelProviders()
    setBundle(nextBundle)
    setRoutes(nextBundle.routes)
    return nextBundle
  }

  useEffect(() => {
    let active = true
    getModelProviders()
      .then((nextBundle) => {
        if (!active) return
        setBundle(nextBundle)
        setRoutes(nextBundle.routes)
      })
      .catch((loadError) => {
        if (active) setError(loadError instanceof Error ? loadError.message : 'Could not load model providers')
      })
      .finally(() => {
        if (active) setLoading(false)
      })
    return () => {
      active = false
    }
  }, [])

  const selectedProvider = bundle?.providers.find((provider) => provider.id === selectedProviderId) ?? null
  const configuredProviders = bundle?.providers.filter((provider) => provider.config?.enabled) ?? []
  const configuredCount = configuredProviders.length
  const connectedCount = configuredProviders.filter((provider) => provider.config?.status === 'connected').length

  const openProvider = (provider: ModelProvider) => {
    setSelectedProviderId(provider.id)
    setForm(createProviderForm(provider))
    setTestMessage(null)
    setError(null)
  }

  const closeProvider = () => {
    setSelectedProviderId(null)
    setForm(null)
    setTestMessage(null)
    setError(null)
  }

  const saveConnection = async () => {
    if (!selectedProvider || !form) return
    setSaving(true)
    setError(null)
    try {
      await saveModelProvider(selectedProvider.id, {
        ...form,
        apiKey: form.apiKey || undefined,
      })
      const nextBundle = await load()
      const refreshed = nextBundle.providers.find((provider) => provider.id === selectedProvider.id)
      if (refreshed) setForm(createProviderForm(refreshed))
      onSaved(`${selectedProvider.label} configuration was encrypted and saved.`)
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : 'Could not save provider')
    } finally {
      setSaving(false)
    }
  }

  const testConnection = async () => {
    if (!selectedProvider) return
    setTesting(true)
    setError(null)
    setTestMessage(null)
    try {
      const result = await testModelProvider(selectedProvider.id)
      setTestMessage({ ok: result.ok, text: result.modelCount !== undefined ? `${result.message} · ${result.modelCount} models found` : result.message })
      await load()
    } catch (testError) {
      setTestMessage({ ok: false, text: testError instanceof Error ? testError.message : 'Connection test failed' })
    } finally {
      setTesting(false)
    }
  }

  const removeConnection = async () => {
    if (!selectedProvider?.config) return
    if (!window.confirm(`Remove the ${selectedProvider.label} connection and its encrypted credential?`)) return
    setSaving(true)
    setError(null)
    try {
      await removeModelProvider(selectedProvider.id)
      await load()
      closeProvider()
      onSaved(`${selectedProvider.label} was disconnected.`)
    } catch (removeError) {
      setError(removeError instanceof Error ? removeError.message : 'Could not remove provider')
    } finally {
      setSaving(false)
    }
  }

  const updateRouteProvider = (capability: ModelCapability, providerId: string) => {
    if (!providerId) {
      setRoutes((current) => ({ ...current, [capability]: null }))
      return
    }
    const provider = configuredProviders.find((item) => item.id === providerId)
    const suggestedModel = provider?.config?.models[capability] ?? ''
    setRoutes((current) => ({
      ...current,
      [capability]: { provider: providerId, model: suggestedModel },
    }))
  }

  const updateRouteModel = (capability: ModelCapability, model: string) => {
    setRoutes((current) => {
      const route = current[capability]
      return route ? { ...current, [capability]: { ...route, model } } : current
    })
  }

  const saveRouting = async () => {
    setSaving(true)
    setError(null)
    try {
      const savedRoutes = await saveModelRoutes({
        llm: routes.llm,
        vlm: routes.vlm,
        image: routes.image,
        video: routes.video,
      })
      setRoutes(savedRoutes)
      onSaved('Default model routing was saved.')
    } catch (routingError) {
      setError(routingError instanceof Error ? routingError.message : 'Could not save model routing')
    } finally {
      setSaving(false)
    }
  }

  if (loading) {
    return <div className="page models-loading"><LoaderCircle size={24} className="spin" /><p>Loading model configuration…</p></div>
  }

  return (
    <div className="page models-page">
      <section className="collection-heading models-heading">
        <div>
          <p className="eyebrow">AI INFRASTRUCTURE</p>
          <h2>Models & providers</h2>
          <p className="page-subtitle">Connect your APIs, choose model IDs, and control which model handles each creative task.</p>
        </div>
        <div className="model-health-summary">
          <span><Network size={15} /></span>
          <div><strong>{configuredCount} configured</strong><small>{connectedCount} connection{connectedCount === 1 ? '' : 's'} verified</small></div>
        </div>
      </section>

      {error && !selectedProvider ? <div className="models-page-error" role="alert"><CircleAlert size={15} /> {error}</div> : null}

      <section className="model-routing-panel">
        <div className="model-section-heading">
          <div><span><Cpu size={18} /></span><div><p className="eyebrow">DEFAULT ROUTING</p><h3>Assign models to creative tasks</h3><small>Only configured and enabled providers can be selected.</small></div></div>
          <button type="button" className="primary-button" onClick={() => void saveRouting()} disabled={saving}><Save size={14} /> Save routing</button>
        </div>
        <div className="model-route-grid">
          {(Object.keys(capabilityMeta) as ModelCapability[]).map((capability) => {
            const meta = capabilityMeta[capability]
            const Icon = meta.icon
            const availableProviders = configuredProviders.filter((provider) => provider.capabilities.includes(capability))
            return (
              <article className="model-route-card" key={capability}>
                <div className={`route-icon route-${capability}`}><Icon size={18} /></div>
                <span className="route-short-label">{meta.shortLabel}</span>
                <h4>{meta.label}</h4>
                <p>{meta.description}</p>
                <label>
                  <span>Provider</span>
                  <div className="model-select-wrap">
                    <select value={routes[capability]?.provider ?? ''} onChange={(event) => updateRouteProvider(capability, event.target.value)}>
                      <option value="">Not assigned</option>
                      {availableProviders.map((provider) => <option value={provider.id} key={provider.id}>{provider.label}</option>)}
                    </select>
                    <ChevronDown size={13} />
                  </div>
                </label>
                <label>
                  <span>Model ID</span>
                  <input
                    value={routes[capability]?.model ?? ''}
                    onChange={(event) => updateRouteModel(capability, event.target.value)}
                    placeholder={routes[capability] ? 'Enter exact model ID' : 'Choose a provider first'}
                    disabled={!routes[capability]}
                  />
                </label>
              </article>
            )
          })}
        </div>
      </section>

      <section className="provider-section">
        <div className="provider-section-heading">
          <div><p className="eyebrow">PROVIDER CONNECTIONS</p><h3>Connect model APIs</h3><p>Credentials are encrypted before storage and never returned to this page.</p></div>
          <span><ShieldCheck size={14} /> AES-256-GCM encrypted</span>
        </div>
        <div className="provider-grid">
          {bundle?.providers.map((provider) => (
            <article className="provider-card" key={provider.id}>
              <div className="provider-card-head">
                <span className={`provider-logo provider-${providerTones[provider.id] ?? 'slate'}`}>{provider.label.slice(0, 2)}</span>
                <ConnectionStatus provider={provider} />
              </div>
              <h4>{provider.label}</h4>
              <p>{provider.description}</p>
              <div className="provider-capabilities">
                {provider.capabilities.map((capability) => <span key={capability}>{capabilityMeta[capability].shortLabel}</span>)}
              </div>
              <button type="button" onClick={() => openProvider(provider)}>
                {provider.config ? 'Manage connection' : 'Configure provider'} <Link2 size={13} />
              </button>
            </article>
          ))}
        </div>
      </section>

      {selectedProvider && form ? (
        <>
          <button type="button" className="model-drawer-overlay" onClick={closeProvider} aria-label="Close provider settings" />
          <aside className="model-config-drawer" aria-label={`${selectedProvider.label} configuration`}>
            <header>
              <div className={`provider-logo provider-${providerTones[selectedProvider.id] ?? 'slate'}`}>{selectedProvider.label.slice(0, 2)}</div>
              <div><p className="eyebrow">PROVIDER SETUP</p><h3>{selectedProvider.label}</h3></div>
              <button type="button" className="icon-button" onClick={closeProvider} aria-label="Close"><X size={18} /></button>
            </header>
            <div className="drawer-security-note"><LockKeyhole size={15} /><p><strong>Credential protection</strong><span>Keys are encrypted on the server and never sent back to the browser.</span></p></div>
            <div className="model-config-form">
              <label><span>Connection name</span><input value={form.label} onChange={(event) => setForm((current) => current ? { ...current, label: event.target.value } : current)} /></label>
              <label><span>API base URL</span><input value={form.baseUrl} onChange={(event) => setForm((current) => current ? { ...current, baseUrl: event.target.value } : current)} placeholder="https://api.provider.com/v1" /></label>
              {selectedProvider.id === 'ollama' ? null : (
                <label>
                  <span>API key {selectedProvider.config?.hasApiKey ? <em><Check size={10} /> Saved</em> : null}</span>
                  <div className="secret-input"><KeyRound size={14} /><input type="password" autoComplete="new-password" value={form.apiKey} onChange={(event) => setForm((current) => current ? { ...current, apiKey: event.target.value } : current)} placeholder={selectedProvider.config?.hasApiKey ? 'Leave blank to keep saved key' : selectedProvider.requiresApiKey ? 'Required' : 'Optional'} /></div>
                </label>
              )}
              <div className="model-id-section">
                <div><p>Default model IDs</p><small>Use the exact IDs supplied by your provider.</small></div>
                {selectedProvider.capabilities.map((capability) => (
                  <label key={capability}>
                    <span>{capabilityMeta[capability].label}</span>
                    <input
                      value={form.models[capability]}
                      onChange={(event) => setForm((current) => current ? { ...current, models: { ...current.models, [capability]: event.target.value } } : current)}
                      placeholder={`${capabilityMeta[capability].shortLabel} model ID`}
                    />
                  </label>
                ))}
              </div>
              <label className="provider-enabled-row">
                <span><strong>Enable provider</strong><small>Allow this provider to appear in model routing.</small></span>
                <input type="checkbox" checked={form.enabled} onChange={(event) => setForm((current) => current ? { ...current, enabled: event.target.checked } : current)} />
                <i />
              </label>
            </div>
            {testMessage ? <div className={`connection-test-result ${testMessage.ok ? 'success' : 'failed'}`}>{testMessage.ok ? <Check size={14} /> : <CircleAlert size={14} />}<span>{testMessage.text}</span></div> : null}
            {error ? <div className="drawer-error" role="alert"><CircleAlert size={14} /> {error}</div> : null}
            <footer>
              {selectedProvider.config ? <button type="button" className="remove-provider-button" onClick={() => void removeConnection()} disabled={saving}><Trash2 size={14} /> Remove</button> : null}
              <button type="button" className="secondary-button" onClick={() => void testConnection()} disabled={!selectedProvider.config || testing}>{testing ? <LoaderCircle size={14} className="spin" /> : <PlugZap size={14} />} Test</button>
              <button type="button" className="primary-button" onClick={() => void saveConnection()} disabled={saving}>{saving ? <LoaderCircle size={14} className="spin" /> : <Save size={14} />} Save connection</button>
            </footer>
          </aside>
        </>
      ) : null}
    </div>
  )
}
