import { useState } from 'react'
import {
  AlignCenter,
  AlignLeft,
  ArrowLeft,
  Check,
  ChevronDown,
  Download,
  Image,
  Layers3,
  Lock,
  Minus,
  MousePointer2,
  Plus,
  Redo2,
  ScanLine,
  Sparkles,
  Type,
  Undo2,
  ZoomIn,
} from 'lucide-react'
import { CreativeArtwork } from '../components/CreativeArtwork'
import { initialCreatives } from '../data'
import type { Creative, CreativeVariant } from '../types'

interface EditorPageProps {
  creativeId: number
  onBack: () => void
  onSave: () => void
}

const colorOptions: CreativeVariant[] = ['citrus', 'lavender', 'midnight', 'sand']
const blankCreative: Creative = {
  id: 0,
  title: 'Untitled creative',
  headline: 'Add your headline',
  subline: 'Add supporting copy.',
  cta: 'Call to action',
  score: 0,
  format: '1:1',
  variant: 'citrus',
  status: 'draft',
}

export function EditorPage({ creativeId, onBack, onSave }: EditorPageProps) {
  const creative = initialCreatives.find((item) => item.id === creativeId) ?? blankCreative
  const [headline, setHeadline] = useState(creative.headline)
  const [subline, setSubline] = useState(creative.subline)
  const [cta, setCta] = useState(creative.cta)
  const [variant, setVariant] = useState<CreativeVariant>(creative.variant)
  const [selectedLayer, setSelectedLayer] = useState('headline')
  const [saved, setSaved] = useState(false)

  const save = () => {
    setSaved(true)
    onSave()
    window.setTimeout(() => setSaved(false), 1600)
  }

  return (
    <div className="editor-page">
      <header className="editor-header">
        <button type="button" className="back-button" onClick={onBack}><ArrowLeft size={17} /> Back</button>
        <div className="editor-file">
          <strong>{creative.title}</strong>
          <span>{saved ? <><Check size={12} /> Saved</> : 'All changes saved'}</span>
        </div>
        <div className="editor-history">
          <button type="button" aria-label="Undo"><Undo2 size={17} /></button>
          <button type="button" aria-label="Redo"><Redo2 size={17} /></button>
        </div>
        <div className="editor-header-spacer" />
        <button type="button" className="secondary-button"><ScanLine size={15} /> Score <strong>94</strong></button>
        <button type="button" className="primary-button" onClick={save}><Download size={15} /> Export</button>
      </header>

      <div className="editor-shell">
        <aside className="editor-tools">
          <button type="button" className="active"><MousePointer2 size={19} /><span>Select</span></button>
          <button type="button"><Type size={19} /><span>Text</span></button>
          <button type="button"><Image size={19} /><span>Media</span></button>
          <button type="button"><Layers3 size={19} /><span>Elements</span></button>
          <button type="button"><Sparkles size={19} /><span>AI tools</span></button>
        </aside>

        <aside className="layers-panel">
          <div className="layers-head"><strong>Layers</strong><button type="button"><Plus size={15} /></button></div>
          <div className="layer-list">
            <button type="button" onClick={() => setSelectedLayer('logo')} className={selectedLayer === 'logo' ? 'active' : ''}>
              <span className="layer-icon">K</span><span><strong>Brand logo</strong><small>Image</small></span><Lock size={13} />
            </button>
            <button type="button" onClick={() => setSelectedLayer('headline')} className={selectedLayer === 'headline' ? 'active' : ''}>
              <span className="layer-icon"><Type size={14} /></span><span><strong>Headline</strong><small>{headline}</small></span>
            </button>
            <button type="button" onClick={() => setSelectedLayer('subline')} className={selectedLayer === 'subline' ? 'active' : ''}>
              <span className="layer-icon"><Type size={14} /></span><span><strong>Body copy</strong><small>{subline}</small></span>
            </button>
            <button type="button" onClick={() => setSelectedLayer('cta')} className={selectedLayer === 'cta' ? 'active' : ''}>
              <span className="layer-icon"><MousePointer2 size={14} /></span><span><strong>CTA button</strong><small>{cta}</small></span>
            </button>
            <button type="button" onClick={() => setSelectedLayer('product')} className={selectedLayer === 'product' ? 'active' : ''}>
              <span className="layer-icon"><Image size={14} /></span><span><strong>Product image</strong><small>kora-cold-brew.png</small></span>
            </button>
            <button type="button" onClick={() => setSelectedLayer('background')} className={selectedLayer === 'background' ? 'active' : ''}>
              <span className={`layer-color layer-color-${variant}`} /><span><strong>Background</strong><small>Brand gradient</small></span><Lock size={13} />
            </button>
          </div>
        </aside>

        <main className="editor-canvas-area">
          <div className="canvas-ruler ruler-top"><span>0</span><span>200</span><span>400</span><span>600</span><span>800</span><span>1080</span></div>
          <div className="canvas-ruler ruler-left"><span>0</span><span>200</span><span>400</span><span>600</span><span>800</span><span>1080</span></div>
          <div className="artboard-wrap">
            <CreativeArtwork
              headline={headline}
              subline={subline}
              cta={cta}
              variant={variant}
              className="editor-artboard"
              showChrome
            />
            <div className={`selection-box select-${selectedLayer}`}>
              <i /><i /><i /><i />
              <span>{selectedLayer}</span>
            </div>
          </div>
          <div className="zoom-control">
            <button type="button"><Minus size={14} /></button>
            <span><ZoomIn size={13} /> 72%</span>
            <button type="button"><Plus size={14} /></button>
          </div>
        </main>

        <aside className="properties-panel">
          <div className="properties-head"><strong>Properties</strong><button type="button"><ChevronDown size={15} /></button></div>
          <section className="property-section">
            <p>Content</p>
            <label><span>Headline</span><textarea value={headline} onChange={(event) => setHeadline(event.target.value)} /></label>
            <button type="button" className="ai-suggest"><Sparkles size={14} /> Suggest stronger options</button>
            <label><span>Body copy</span><textarea value={subline} onChange={(event) => setSubline(event.target.value)} /></label>
            <label><span>Button text</span><input value={cta} onChange={(event) => setCta(event.target.value)} /></label>
          </section>
          <section className="property-section">
            <p>Typography</p>
            <button type="button" className="property-select">Satoshi Bold <ChevronDown size={14} /></button>
            <div className="property-row">
              <label><span>Size</span><input defaultValue="72" /></label>
              <label><span>Line</span><input defaultValue="0.95" /></label>
            </div>
            <div className="align-buttons">
              <button type="button" className="active"><AlignLeft size={15} /></button>
              <button type="button"><AlignCenter size={15} /></button>
            </div>
          </section>
          <section className="property-section">
            <p>Color system</p>
            <div className="color-options">
              {colorOptions.map((color) => (
                <button
                  type="button"
                  className={`color-option color-${color} ${variant === color ? 'active' : ''}`}
                  onClick={() => setVariant(color)}
                  aria-label={`Use ${color} color theme`}
                  key={color}
                >
                  {variant === color ? <Check size={12} /> : null}
                </button>
              ))}
            </div>
          </section>
          <section className="property-section quick-fixes">
            <p><Sparkles size={13} /> Quick improvements</p>
            <button type="button"><span>Shorten headline</span><em>+4 pts</em></button>
            <button type="button"><span>Increase CTA contrast</span><em>+3 pts</em></button>
          </section>
        </aside>
      </div>
    </div>
  )
}
