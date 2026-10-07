import { useRef, useState } from 'react'
import {
  ArrowLeft,
  ArrowRight,
  BadgeCheck,
  Box,
  Camera,
  Check,
  ChevronRight,
  Clapperboard,
  Download,
  Film,
  Image,
  Images,
  Layers3,
  MessageSquareText,
  PackageOpen,
  Palette,
  Play,
  Plus,
  RefreshCw,
  Search,
  Sparkles,
  Upload,
  UserRound,
  WandSparkles,
} from 'lucide-react'
import {
  approveGeneration,
  createGeneration,
  reviseGeneration,
  uploadProduct,
  waitForGeneration,
  type GenerationOutput,
  type GenerationRecord,
  type UploadRecord,
} from '../lib/api'

type ProjectCategory = 'all' | 'image' | 'video' | 'social'
type ToolIcon = typeof Image

interface CreationTool {
  id: string
  number: string
  title: string
  description: string
  category: Exclude<ProjectCategory, 'all'>
  mode: 'Template' | 'AI generated'
  icon: ToolIcon
  visual: string
  badge?: string
  choicesLabel: string
  choices: string[]
  promptLabel?: string
}

const creationTools: CreationTool[] = [
  {
    id: 'template-cover',
    number: '01',
    title: 'Template cover generator',
    description: 'Place your product into polished, conversion-ready cover layouts.',
    category: 'image',
    mode: 'Template',
    icon: Layers3,
    visual: 'lime',
    choicesLabel: 'Template direction',
    choices: ['Bold sale', 'Minimal launch', 'Editorial', 'Marketplace'],
  },
  {
    id: 'ai-cover',
    number: '02',
    title: 'AI cover generator',
    description: 'Create an original cover around your product in a style you choose.',
    category: 'image',
    mode: 'AI generated',
    icon: WandSparkles,
    visual: 'violet',
    badge: 'Popular',
    choicesLabel: 'Visual style',
    choices: ['Luxury', 'Playful 3D', 'Soft editorial', 'Future tech'],
    promptLabel: 'Describe the cover you have in mind',
  },
  {
    id: 'template-photo',
    number: '03',
    title: 'Studio photo templates',
    description: 'Turn a simple product photo into professional studio compositions.',
    category: 'image',
    mode: 'Template',
    icon: Camera,
    visual: 'peach',
    choicesLabel: 'Studio setup',
    choices: ['Clean shadow', 'Color blocks', 'Reflective', 'Ingredient set'],
  },
  {
    id: 'ai-photo',
    number: '04',
    title: 'AI professional photos',
    description: 'Generate campaign shots in environments that match your brand.',
    category: 'image',
    mode: 'AI generated',
    icon: Sparkles,
    visual: 'sky',
    badge: 'Best results',
    choicesLabel: 'Environment',
    choices: ['Sunlit kitchen', 'City at night', 'Alpine nature', 'Premium studio'],
    promptLabel: 'Add art direction or product details',
  },
  {
    id: 'social-thread',
    number: '05',
    title: 'AI social thread',
    description: 'Build a connected visual story for carousels, threads, and slideshows.',
    category: 'social',
    mode: 'AI generated',
    icon: Images,
    visual: 'coral',
    badge: 'New',
    choicesLabel: 'Publishing format',
    choices: ['Instagram carousel', 'TikTok slideshow', 'X thread', 'LinkedIn document'],
    promptLabel: 'What does the product do and what story should the thread tell?',
  },
  {
    id: 'ugc-video',
    number: '06',
    title: 'UGC video builder',
    description: 'Create scene-by-scene UGC with an avatar, approved flow, and revisions.',
    category: 'video',
    mode: 'AI generated',
    icon: UserRound,
    visual: 'rose',
    badge: 'Most powerful',
    choicesLabel: 'Presenter',
    choices: ['Real creator — Maya', 'Real creator — Noah', 'Animated creator', 'Upload my avatar'],
    promptLabel: 'Explain the desired video flow, or let AI write it',
  },
  {
    id: 'artistic-motion',
    number: '07',
    title: 'Artistic product motion',
    description: 'Transform a product image into a cinematic, art-directed motion clip.',
    category: 'video',
    mode: 'AI generated',
    icon: Film,
    visual: 'midnight',
    choicesLabel: 'Motion style',
    choices: ['Liquid reveal', 'Floating gravity', 'Light trails', 'Stop motion'],
    promptLabel: 'Describe the movement, mood, and camera',
  },
  {
    id: 'explainer',
    number: '08',
    title: 'Product explainer',
    description: 'Turn product benefits into a clear short-form visual explanation.',
    category: 'video',
    mode: 'AI generated',
    icon: MessageSquareText,
    visual: 'blue',
    choicesLabel: 'Explainer format',
    choices: ['Problem → solution', '3 key benefits', 'How it works', 'Before & after'],
    promptLabel: 'Paste the product benefits or website copy',
  },
  {
    id: 'demo-video',
    number: '09',
    title: 'Product demo video',
    description: 'Show the product in use with close-ups, callouts, and guided steps.',
    category: 'video',
    mode: 'Template',
    icon: Play,
    visual: 'mint',
    choicesLabel: 'Demo structure',
    choices: ['Fast hands-on', 'Step by step', 'Feature focus', 'Silent aesthetic'],
  },
  {
    id: 'spokesperson',
    number: '10',
    title: 'AI spokesperson',
    description: 'Create a concise pitch delivered by a brand-ready digital presenter.',
    category: 'video',
    mode: 'AI generated',
    icon: Clapperboard,
    visual: 'gold',
    choicesLabel: 'Presenter style',
    choices: ['Friendly expert', 'Founder story', 'High energy', 'Calm educator'],
    promptLabel: 'Describe the audience, offer, and key message',
  },
  {
    id: 'unboxing',
    number: '11',
    title: 'AI unboxing sequence',
    description: 'Generate an anticipation-led unboxing story from packaging to payoff.',
    category: 'social',
    mode: 'AI generated',
    icon: PackageOpen,
    visual: 'orange',
    choicesLabel: 'Unboxing mood',
    choices: ['Premium reveal', 'Cozy creator', 'ASMR details', 'Fast surprise'],
    promptLabel: 'What should viewers notice first?',
  },
  {
    id: 'campaign-kit',
    number: '12',
    title: 'Multi-format campaign kit',
    description: 'Generate one consistent concept across covers, stories, posts, and video.',
    category: 'social',
    mode: 'AI generated',
    icon: Box,
    visual: 'prism',
    badge: 'Full campaign',
    choicesLabel: 'Campaign objective',
    choices: ['Launch', 'Seasonal sale', 'Always-on', 'Retargeting'],
    promptLabel: 'Describe your campaign message and offer',
  },
]

const categoryTabs: Array<{ id: ProjectCategory; label: string }> = [
  { id: 'all', label: 'All tools' },
  { id: 'image', label: 'Images' },
  { id: 'video', label: 'Videos' },
  { id: 'social', label: 'Social stories' },
]

interface NewProjectPageProps {
  onOpenClassicGenerator: () => void
  onProjectCreated: (title: string) => void
}

function ToolVisual({ tool, compact = false }: { tool: CreationTool; compact?: boolean }) {
  const Icon = tool.icon
  return (
    <div className={`tool-visual visual-${tool.visual} ${compact ? 'compact' : ''}`}>
      <span className="tool-visual-grid" />
      <span className="visual-orb orb-a" />
      <span className="visual-orb orb-b" />
      <span className="visual-product">
        <i />
        <b>MONO</b>
        <small>01</small>
      </span>
      <span className="visual-icon"><Icon size={compact ? 16 : 20} /></span>
      {tool.category === 'video' ? <span className="visual-play"><Play size={12} fill="currentColor" /></span> : null}
      {tool.id === 'social-thread' ? (
        <span className="visual-thread"><i /><i /><i /></span>
      ) : null}
    </div>
  )
}

function ResultPreview({ index, tool, output, active, onSelect }: {
  index: number
  tool: CreationTool
  output?: GenerationOutput
  active: boolean
  onSelect: () => void
}) {
  return (
    <button
      type="button"
      className={`generated-option ${active ? 'selected' : ''}`}
      onClick={onSelect}
      aria-label={`Select generated option ${index + 1}`}
    >
      <div className={`result-art result-${tool.visual} result-${index + 1} ${output ? 'has-backend-image' : ''}`}>
        {output ? <img className="result-backend-image" src={output.url} alt="" /> : null}
        <span className="result-brand">MONO / OBJECTS</span>
        <div className="result-product"><i /><strong>MONO</strong></div>
        <p>{index % 2 === 0 ? 'Designed for your everyday.' : 'Make the ordinary iconic.'}</p>
        {tool.category === 'video' ? <span className="result-duration">00:0{index + 6}</span> : null}
      </div>
      <span className="result-meta">
        <span>Option {index + 1}</span>
        {active ? <BadgeCheck size={16} /> : <span className="select-circle" />}
      </span>
    </button>
  )
}

function ProjectConfigurator({ tool, onBack, onCreated }: {
  tool: CreationTool
  onBack: () => void
  onCreated: (title: string) => void
}) {
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [upload, setUpload] = useState<UploadRecord | null>(null)
  const [uploading, setUploading] = useState(false)
  const [choice, setChoice] = useState(tool.choices[0])
  const [prompt, setPrompt] = useState('')
  const [stage, setStage] = useState<'setup' | 'generating' | 'results'>('setup')
  const [selectedResult, setSelectedResult] = useState(0)
  const [changeRequest, setChangeRequest] = useState('')
  const [generation, setGeneration] = useState<GenerationRecord | null>(null)
  const [error, setError] = useState<string | null>(null)

  const generate = async () => {
    if (!upload) {
      setError('Upload a product photo or use the demo product first.')
      return
    }
    setError(null)
    setStage('generating')
    try {
      const created = await createGeneration({
        toolId: tool.id,
        title: `${tool.title} · ${choice}`,
        choice,
        prompt,
        uploadId: upload.id,
      })
      const completed = await waitForGeneration(created.id)
      setGeneration(completed)
      setSelectedResult(0)
      setStage('results')
    } catch (generationError) {
      setError(generationError instanceof Error ? generationError.message : 'Generation failed')
      setStage('setup')
    }
  }

  const handleFile = async (file: File) => {
    setUploading(true)
    setError(null)
    try {
      setUpload(await uploadProduct(file))
    } catch (uploadError) {
      setError(uploadError instanceof Error ? uploadError.message : 'Upload failed')
    } finally {
      setUploading(false)
    }
  }

  const applyChange = async () => {
    if (!generation || !changeRequest.trim()) return
    setStage('generating')
    setError(null)
    try {
      const revision = await reviseGeneration(generation.id, changeRequest)
      const completed = await waitForGeneration(revision.id)
      setGeneration(completed)
      setChangeRequest('')
      setSelectedResult(0)
      setStage('results')
    } catch (revisionError) {
      setError(revisionError instanceof Error ? revisionError.message : 'Revision failed')
      setStage('results')
    }
  }

  const approve = async () => {
    const output = generation?.outputs[selectedResult]
    if (!generation || !output) return
    setError(null)
    try {
      await approveGeneration(generation.id, output.id)
      onCreated(tool.title)
    } catch (approvalError) {
      setError(approvalError instanceof Error ? approvalError.message : 'Approval failed')
    }
  }

  if (stage === 'generating') {
    return (
      <section className="project-generating" aria-live="polite">
        <div className="generation-orbit">
          <ToolVisual tool={tool} compact />
          <span />
          <span />
        </div>
        <p className="eyebrow">PRODUCTMARKETER AI</p>
        <h2>Building your {tool.title.toLowerCase()}</h2>
        <p>Composing the product, refining light, and preparing variations.</p>
        <div className="generation-progress"><span /></div>
        <small>Usually takes less than a minute</small>
      </section>
    )
  }

  if (stage === 'results') {
    return (
      <div className="project-config-page result-page">
        <button type="button" className="config-back" onClick={() => setStage('setup')}>
          <ArrowLeft size={15} /> Back to setup
        </button>
        <section className="result-heading">
          <div>
            <span className="result-success"><Check size={13} /> 4 options generated</span>
            <h2>Choose your favorite direction</h2>
            <p>Select an option, request a change, or regenerate until it feels right.</p>
          </div>
          <button type="button" className="secondary-button" onClick={generate}><RefreshCw size={14} /> Regenerate all</button>
        </section>
        {tool.id === 'ugc-video' ? (
          <section className="storyboard-strip">
            <div className="storyboard-heading">
              <div><p className="eyebrow">APPROVED FLOW</p><h3>Your UGC storyboard</h3></div>
              <span>4 scenes · 24 sec</span>
            </div>
            <div className="storyboard-scenes">
              {(generation?.scenes.length ? generation.scenes : [
                { id: 'hook', title: 'Hook', script: '“I finally found…”' },
                { id: 'problem', title: 'Problem', script: 'Scene approved' },
                { id: 'product', title: 'Product moment', script: 'Scene approved' },
                { id: 'cta', title: 'Call to action', script: '“Try it today.”' },
              ]).map((scene, index) => (
                <article key={scene.id}>
                  <span>{index + 1}</span>
                  <div className={`story-frame frame-${index + 1}`}><UserRound size={22} /><Play size={11} fill="currentColor" /></div>
                  <strong>{scene.title}</strong>
                  <small>{scene.script}</small>
                  <button type="button">Change scene</button>
                </article>
              ))}
            </div>
          </section>
        ) : null}
        <div className="generated-results-grid">
          {[0, 1, 2, 3].map((index) => (
            <ResultPreview
              key={index}
              index={index}
              tool={tool}
              output={generation?.outputs[index]}
              active={selectedResult === index}
              onSelect={() => setSelectedResult(index)}
            />
          ))}
        </div>
        <section className="change-request-bar">
          <span><MessageSquareText size={18} /></span>
          <label>
            <strong>Suggest a change to option {selectedResult + 1}</strong>
            <input
              value={changeRequest}
              onChange={(event) => setChangeRequest(event.target.value)}
              placeholder="e.g. Make the background warmer and add a softer shadow"
            />
          </label>
          <button
            type="button"
            className="secondary-button"
            onClick={applyChange}
            disabled={!changeRequest.trim()}
          >
            Apply change
          </button>
        </section>
        <div className="result-actions">
          <p><BadgeCheck size={16} /> Option {selectedResult + 1} selected</p>
          <button type="button" className="secondary-button"><Download size={15} /> Download</button>
          <button
            type="button"
            className="primary-button"
            onClick={approve}
          >
            Approve & save project <ArrowRight size={15} />
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="project-config-page">
      <button type="button" className="config-back" onClick={onBack}>
        <ArrowLeft size={15} /> All creation tools
      </button>
      <section className="config-heading">
        <ToolVisual tool={tool} compact />
        <div>
          <span className="config-mode"><Sparkles size={12} /> {tool.mode}</span>
          <h2>{tool.title}</h2>
          <p>{tool.description}</p>
        </div>
        <span className="config-step">Setup · 1 of 3</span>
      </section>

      <div className="config-layout">
        <div className="config-main">
          <section className="config-card">
            <div className="config-card-heading">
              <span>01</span>
              <div><h3>Upload your product</h3><p>Use a clear PNG or JPG. A simple background works best.</p></div>
            </div>
            <input
              ref={fileInputRef}
              className="visually-hidden"
              type="file"
              accept="image/png,image/jpeg,image/webp"
              onChange={(event) => {
                const file = event.target.files?.[0]
                if (file) void handleFile(file)
              }}
            />
            <button
              type="button"
              className={`product-upload ${upload ? 'uploaded' : ''}`}
              onClick={() => fileInputRef.current?.click()}
              disabled={uploading}
            >
              {upload ? (
                <>
                  <span className="uploaded-product"><i /><b>MONO</b></span>
                  <span><strong>{upload.name}</strong><small>{Math.max(1, Math.round(upload.size / 1024))} KB · Stored securely</small></span>
                  <em><Check size={14} /> Ready</em>
                </>
              ) : (
                <>
                  <span><Upload size={19} /></span>
                  <strong>{uploading ? 'Uploading product…' : 'Drop your product photo here'}</strong>
                  <small>or click to browse · PNG, JPG or WEBP up to 20MB</small>
                </>
              )}
            </button>
            {error ? <p className="config-error" role="alert">{error}</p> : null}
          </section>

          <section className="config-card">
            <div className="config-card-heading">
              <span>02</span>
              <div><h3>Choose {tool.choicesLabel.toLowerCase()}</h3><p>Preview the direction before generation.</p></div>
            </div>
            <div className="direction-options">
              {tool.choices.map((item, index) => (
                <button
                  type="button"
                  className={choice === item ? 'selected' : ''}
                  onClick={() => setChoice(item)}
                  key={item}
                >
                  <span className={`direction-preview direction-${index + 1}`}><i /><b /></span>
                  <strong>{item}</strong>
                  <small>{index % 2 === 0 ? 'Clean · conversion-led' : 'Expressive · brand-led'}</small>
                  <em>{choice === item ? <Check size={12} /> : null}</em>
                </button>
              ))}
            </div>
          </section>

          {tool.mode === 'AI generated' ? (
            <section className="config-card">
              <div className="config-card-heading">
                <span>03</span>
                <div><h3>Give AI more direction</h3><p>Optional, but useful for details that make your product unique.</p></div>
              </div>
              <label className="prompt-field">
                <textarea
                  value={prompt}
                  onChange={(event) => setPrompt(event.target.value)}
                  placeholder={tool.promptLabel}
                  maxLength={500}
                />
                <span><Sparkles size={12} /> AI can improve your prompt</span>
                <small>{prompt.length}/500</small>
              </label>
            </section>
          ) : null}
        </div>

        <aside className="config-summary">
          <p className="eyebrow">PROJECT SUMMARY</p>
          <ToolVisual tool={tool} />
          <dl>
            <div><dt>Tool</dt><dd>{tool.title}</dd></div>
            <div><dt>{tool.choicesLabel}</dt><dd>{choice}</dd></div>
            <div><dt>Output</dt><dd>{tool.category === 'video' ? '4 video concepts' : '4 image options'}</dd></div>
          </dl>
          <button type="button" className="primary-button generate-project-button" onClick={() => void generate()} disabled={!upload || uploading}>
            <Sparkles size={15} /> Generate options
          </button>
          <small><Check size={11} /> Includes commercial usage rights</small>
        </aside>
      </div>
    </div>
  )
}

export function NewProjectPage({ onOpenClassicGenerator, onProjectCreated }: NewProjectPageProps) {
  const [category, setCategory] = useState<ProjectCategory>('all')
  const [query, setQuery] = useState('')
  const [selectedTool, setSelectedTool] = useState<CreationTool | null>(null)

  const normalizedQuery = query.trim().toLowerCase()
  const filteredTools = creationTools.filter((tool) => {
    const matchesCategory = category === 'all' || tool.category === category
    const matchesQuery = !normalizedQuery || `${tool.title} ${tool.description}`.toLowerCase().includes(normalizedQuery)
    return matchesCategory && matchesQuery
  })

  if (selectedTool) {
    return (
      <div className="page new-project-page">
        <ProjectConfigurator
          key={selectedTool.id}
          tool={selectedTool}
          onBack={() => setSelectedTool(null)}
          onCreated={onProjectCreated}
        />
      </div>
    )
  }

  return (
    <div className="page new-project-page">
      <section className="creation-hero">
        <div>
          <span className="creation-hero-badge"><Sparkles size={13} /> CREATE WITH PRODUCTMARKETER</span>
          <h2>What do you want to make?</h2>
          <p>Start with one product photo. Build studio images, connected stories, or complete videos.</p>
        </div>
        <div className="creation-hero-art" aria-hidden="true">
          <span className="hero-card hero-card-one"><Image size={18} /></span>
          <span className="hero-card hero-card-two"><Film size={18} /></span>
          <span className="hero-card hero-card-three"><Palette size={18} /></span>
          <span className="hero-spark"><Sparkles size={22} /></span>
        </div>
      </section>

      <section className="tool-browser">
        <div className="tool-browser-heading">
          <div><p className="eyebrow">CREATION STUDIO</p><h3>Choose a workflow</h3></div>
          <label className="tool-search"><Search size={15} /><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search tools" /></label>
        </div>
        <div className="category-tabs" role="tablist" aria-label="Creation categories">
          {categoryTabs.map((tab) => (
            <button
              type="button"
              role="tab"
              aria-selected={category === tab.id}
              className={category === tab.id ? 'active' : ''}
              onClick={() => setCategory(tab.id)}
              key={tab.id}
            >
              {tab.label}
              <span>{tab.id === 'all' ? creationTools.length : creationTools.filter((tool) => tool.category === tab.id).length}</span>
            </button>
          ))}
        </div>

        {filteredTools.length ? (
          <div className="creation-tool-grid">
            {filteredTools.map((tool) => (
              <article className="creation-tool-card" key={tool.id}>
                <button type="button" className="tool-card-open" onClick={() => setSelectedTool(tool)}>
                  <ToolVisual tool={tool} />
                  <span className="tool-card-number">{tool.number}</span>
                  {tool.badge ? <span className="tool-card-badge">{tool.badge}</span> : null}
                  <span className="tool-card-copy">
                    <span className="tool-card-mode">{tool.mode}</span>
                    <strong>{tool.title}</strong>
                    <small>{tool.description}</small>
                  </span>
                  <span className="tool-card-footer">
                    <span>{tool.category === 'image' ? 'Image' : tool.category === 'video' ? 'Video' : 'Multi-slide'}</span>
                    <i>Start creating <ChevronRight size={14} /></i>
                  </span>
                </button>
              </article>
            ))}
          </div>
        ) : (
          <div className="empty-tool-search"><Search size={22} /><strong>No tools found</strong><p>Try another keyword or category.</p></div>
        )}
      </section>

      <button type="button" className="classic-generator-link" onClick={onOpenClassicGenerator}>
        <span><Plus size={16} /></span>
        <span><strong>Need a classic static ad?</strong><small>Open the original campaign generator</small></span>
        <ArrowRight size={15} />
      </button>
    </div>
  )
}
