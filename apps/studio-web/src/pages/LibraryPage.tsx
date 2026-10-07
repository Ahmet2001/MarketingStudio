import { useState } from 'react'
import {
  Download,
  Filter,
  FolderPlus,
  Grid2X2,
  Heart,
  MoreHorizontal,
  Search,
  Upload,
} from 'lucide-react'
import { CreativeArtwork } from '../components/CreativeArtwork'
import { ScoreBadge } from '../components/ScoreBadge'
import { initialCreatives } from '../data'

interface LibraryPageProps {
  onEdit: (creativeId: number) => void
}

export function LibraryPage({ onEdit }: LibraryPageProps) {
  const [favorites, setFavorites] = useState(() => new Set<number>())

  const toggleFavorite = (id: number) => {
    setFavorites((current) => {
      const next = new Set(current)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  return (
    <div className="page collection-page">
      <section className="collection-heading">
        <div>
          <p className="eyebrow">ASSET HUB</p>
          <h2>Creative library</h2>
          <p className="page-subtitle">Your generated, uploaded, and downloaded assets.</p>
        </div>
        <div className="heading-actions">
          <button type="button" className="secondary-button"><FolderPlus size={15} /> New folder</button>
          <button type="button" className="primary-button"><Upload size={15} /> Upload asset</button>
        </div>
      </section>

      <section className="library-tabs">
        <button type="button" className="active">All assets <span>0</span></button>
        <button type="button">Generated <span>0</span></button>
        <button type="button">Uploads <span>0</span></button>
        <button type="button">Favorites <span>{favorites.size}</span></button>
      </section>

      <section className="collection-toolbar">
        <label className="collection-search">
          <Search size={16} />
          <input placeholder="Search your library" aria-label="Search your library" />
        </label>
        <button type="button" className="toolbar-button"><Filter size={15} /> Format</button>
        <button type="button" className="toolbar-button">Campaign</button>
        <div className="toolbar-spacer" />
        <button type="button" className="toolbar-button"><Grid2X2 size={15} /> Newest first</button>
      </section>

      <div className="library-grid">
        {initialCreatives.length === 0 ? (
          <div className="library-empty-state">
            <Upload size={24} />
            <strong>Your library is empty</strong>
            <p>Upload an asset or approve a generated result to add it here.</p>
            <button type="button" className="primary-button"><Upload size={14} /> Upload asset</button>
          </div>
        ) : [...initialCreatives, ...initialCreatives].map((creative, index) => {
          const id = index + 1
          return (
            <article className="library-asset-card" key={id}>
              <div className="library-artwork-wrap">
                <CreativeArtwork
                  headline={creative.headline}
                  subline={creative.subline}
                  cta={creative.cta}
                  variant={creative.variant}
                />
                <ScoreBadge score={Math.max(79, creative.score - Math.floor(index / 3))} />
                <div className="asset-hover-actions">
                  <button type="button" onClick={() => onEdit(creative.id)}>Edit</button>
                  <button type="button" aria-label="Download creative"><Download size={15} /></button>
                  <button
                    type="button"
                    className={favorites.has(id) ? 'favorite' : ''}
                    onClick={() => toggleFavorite(id)}
                    aria-label={favorites.has(id) ? 'Remove from favorites' : 'Add to favorites'}
                  >
                    <Heart size={15} fill={favorites.has(id) ? 'currentColor' : 'none'} />
                  </button>
                </div>
              </div>
              <div className="library-asset-info">
                <div><strong>{creative.title}</strong><small>1080 × 1080 · PNG</small></div>
                <button type="button" className="icon-button"><MoreHorizontal size={17} /></button>
              </div>
            </article>
          )
        })}
      </div>
    </div>
  )
}
