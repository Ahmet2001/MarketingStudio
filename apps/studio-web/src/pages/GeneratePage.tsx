import { useState } from 'react'
import {
  ArrowLeft,
  ArrowRight,
  Check,
  ChevronDown,
  Globe2,
  Image,
  LayoutTemplate,
  LoaderCircle,
  Megaphone,
  MousePointer2,
  ScanSearch,
  Sparkles,
  Upload,
  WandSparkles,
} from 'lucide-react'
import { CreativeArtwork } from '../components/CreativeArtwork'
import type { CreativeVariant } from '../types'

const goals = [
  { id: 'sales', label: 'Drive sales', icon: Megaphone },
  { id: 'traffic', label: 'Get traffic', icon: MousePointer2 },
  { id: 'awareness', label: 'Build awareness', icon: Sparkles },
]

const styles: Array<{ id: CreativeVariant; name: string; note: string }> = [
  { id: 'citrus', name: 'Bold product', note: 'High contrast' },
  { id: 'lavender', name: 'Editorial', note: 'Story first' },
  { id: 'midnight', name: 'Premium dark', note: 'Confident' },
  { id: 'sand', name: 'Natural', note: 'Warm & calm' },
]

const formats = [
  { id: 'square', name: 'Square', size: '1080 × 1080' },
  { id: 'portrait', name: 'Portrait', size: '1080 × 1350' },
  { id: 'story', name: 'Story', size: '1080 × 1920' },
  { id: 'landscape', name: 'Landscape', size: '1200 × 628' },
]

interface GeneratePageProps {
  onBack: () => void
  onComplete: () => void
}

export function GeneratePage({ onBack, onComplete }: GeneratePageProps) {
  const [goal, setGoal] = useState('sales')
  const [style, setStyle] = useState<CreativeVariant>('citrus')
  const [selectedFormats, setSelectedFormats] = useState(() => new Set(['square', 'portrait']))
  const [website, setWebsite] = useState('https://koracoffee.co/cold-brew')
  const [product, setProduct] = useState('Kora seasonal cold brew')
  const [audience, setAudience] = useState('Creative professionals, 24–40, who value quality and convenience')
  const [isGenerating, setIsGenerating] = useState(false)

  const toggleFormat = (format: string) => {
    setSelectedFormats((current) => {
      const next = new Set(current)
      if (next.has(format)) {
        if (next.size > 1) next.delete(format)
      } else {
        next.add(format)
      }
      return next
    })
  }

  const generate = () => {
    setIsGenerating(true)
    window.setTimeout(() => {
      setIsGenerating(false)
      onComplete()
    }, 1800)
  }

  return (
    <div className="page generate-page">
      <div className="generate-heading">
        <button type="button" className="back-button" onClick={onBack}>
          <ArrowLeft size={17} /> Back
        </button>
        <div>
          <div className="generate-title-line">
            <span className="generate-title-icon"><WandSparkles size={18} /></span>
            <h2>Create an ad campaign</h2>
          </div>
          <p>Give us the essentials. ProductMarketer will build the creative system.</p>
        </div>
        <div className="draft-saved"><Check size={13} /> Draft saved</div>
      </div>

      <div className="stepper" aria-label="Campaign creation steps">
        {['Brief', 'Formats', 'Creative direction', 'Review'].map((step, index) => (
          <div className={`stepper-item ${index === 0 ? 'current' : ''}`} key={step}>
            <span>{index + 1}</span>
            <strong>{step}</strong>
          </div>
        ))}
      </div>

      <div className="generate-layout">
        <main className="generate-form">
          <section className="form-section">
            <div className="form-section-heading">
              <span>01</span>
              <div>
                <h3>What are we promoting?</h3>
                <p>We’ll scan your page and use your brand memory to fill the gaps.</p>
              </div>
            </div>
            <div className="form-grid">
              <label className="field full-field">
                <span>Product page or website</span>
                <div className="input-with-icon">
                  <Globe2 size={17} />
                  <input value={website} onChange={(event) => setWebsite(event.target.value)} />
                  <button type="button" className="scan-button"><ScanSearch size={14} /> Scan</button>
                </div>
              </label>
              <label className="field">
                <span>Campaign name</span>
                <input value={product} onChange={(event) => setProduct(event.target.value)} />
              </label>
              <label className="field">
                <span>Brand</span>
                <button type="button" className="select-input">
                  <span className="mini-brand-logo">K</span> Kora Coffee <ChevronDown size={15} />
                </button>
              </label>
              <label className="field full-field">
                <span>Target audience</span>
                <textarea value={audience} onChange={(event) => setAudience(event.target.value)} />
                <small>{audience.length}/240</small>
              </label>
            </div>
            <div className="scan-result">
              <div className="scan-product-image">
                <span className="tiny-can">KORA</span>
              </div>
              <div>
                <span className="success-label"><Check size={12} /> Page scanned</span>
                <strong>Seasonal cold brew — citrus blend</strong>
                <p>Bright, clean energy · ethically sourced · ready to drink</p>
              </div>
              <button type="button">Edit details</button>
            </div>
          </section>

          <section className="form-section">
            <div className="form-section-heading">
              <span>02</span>
              <div>
                <h3>Choose your campaign goal</h3>
                <p>This influences copy, layout hierarchy, and recommendations.</p>
              </div>
            </div>
            <div className="choice-grid goal-grid">
              {goals.map(({ id, label, icon: Icon }) => (
                <button
                  key={id}
                  type="button"
                  className={`choice-card ${goal === id ? 'selected' : ''}`}
                  onClick={() => setGoal(id)}
                >
                  <span><Icon size={19} /></span>
                  <strong>{label}</strong>
                  <i>{goal === id ? <Check size={12} /> : null}</i>
                </button>
              ))}
            </div>
          </section>

          <section className="form-section">
            <div className="form-section-heading">
              <span>03</span>
              <div>
                <h3>Select your formats</h3>
                <p>We’ll intelligently adapt each composition—not just crop it.</p>
              </div>
            </div>
            <div className="choice-grid format-grid">
              {formats.map((format) => (
                <button
                  key={format.id}
                  type="button"
                  className={`format-card ${selectedFormats.has(format.id) ? 'selected' : ''}`}
                  onClick={() => toggleFormat(format.id)}
                >
                  <span className={`format-shape shape-${format.id}`} />
                  <strong>{format.name}</strong>
                  <small>{format.size}</small>
                  <i>{selectedFormats.has(format.id) ? <Check size={12} /> : null}</i>
                </button>
              ))}
            </div>
          </section>

          <section className="form-section">
            <div className="form-section-heading">
              <span>04</span>
              <div>
                <h3>Pick a creative direction</h3>
                <p>Every direction uses your colors, voice, and product truths.</p>
              </div>
            </div>
            <div className="style-grid">
              {styles.map((item) => (
                <button
                  key={item.id}
                  type="button"
                  className={`style-card ${style === item.id ? 'selected' : ''}`}
                  onClick={() => setStyle(item.id)}
                >
                  <span className={`style-swatch swatch-${item.id}`}>
                    <i />
                    <b />
                  </span>
                  <span>
                    <strong>{item.name}</strong>
                    <small>{item.note}</small>
                  </span>
                  <em>{style === item.id ? <Check size={12} /> : null}</em>
                </button>
              ))}
            </div>
            <button type="button" className="upload-style-button">
              <Upload size={17} />
              <span><strong>Match a reference</strong><small>Upload an image to borrow its visual direction</small></span>
              <ArrowRight size={16} />
            </button>
          </section>
        </main>

        <aside className="generate-preview-panel">
          <div className="preview-panel-head">
            <div>
              <span className="live-dot" /> LIVE PREVIEW
            </div>
            <span>Square · 1:1</span>
          </div>
          <CreativeArtwork
            headline="Start bright."
            subline="Small-batch cold brew for your biggest days."
            cta="Shop the drop"
            variant={style}
            className="generate-preview-artwork"
            showChrome
          />
          <div className="preview-insight">
            <span className="preview-score">94</span>
            <div><strong>Strong conversion potential</strong><small>Clear product focus and high CTA contrast.</small></div>
            <Sparkles size={16} />
          </div>
          <div className="preview-summary">
            <div><span><LayoutTemplate size={15} /> Formats</span><strong>{selectedFormats.size}</strong></div>
            <div><span><Image size={15} /> Variations</span><strong>12</strong></div>
            <div><span><Sparkles size={15} /> Est. cost</span><strong>Free</strong></div>
          </div>
          <button type="button" className="generate-cta" onClick={generate} disabled={isGenerating}>
            {isGenerating ? (
              <><LoaderCircle size={17} className="spin" /> Building your campaign…</>
            ) : (
              <><Sparkles size={17} /> Generate 12 creatives <ArrowRight size={17} /></>
            )}
          </button>
          <p className="generate-note">Credits are only used when you download.</p>
        </aside>
      </div>

      {isGenerating ? (
        <div className="generation-overlay" role="status" aria-live="polite">
          <div className="generation-modal">
            <div className="generation-orb"><Sparkles size={28} /></div>
            <h3>Building your campaign</h3>
            <p>Writing copy, composing layouts, and adapting formats…</p>
            <div className="generation-progress"><span /></div>
            <div className="generation-tasks">
              <span><Check size={13} /> Brand context</span>
              <span><Check size={13} /> Campaign angles</span>
              <span className="active"><LoaderCircle size={13} className="spin" /> Creative layouts</span>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  )
}
