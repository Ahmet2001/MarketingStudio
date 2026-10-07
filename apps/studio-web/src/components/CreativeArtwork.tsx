import { Coffee, Sparkles } from 'lucide-react'
import type { CreativeVariant } from '../types'

interface CreativeArtworkProps {
  headline: string
  subline: string
  cta: string
  variant: CreativeVariant
  className?: string
  showChrome?: boolean
}

export function CreativeArtwork({
  headline,
  subline,
  cta,
  variant,
  className = '',
  showChrome = false,
}: CreativeArtworkProps) {
  return (
    <div className={`creative-artwork artwork-${variant} ${className}`}>
      <div className="artwork-grid" aria-hidden="true" />
      <div className="artwork-brand">
        <span className="artwork-brand-mark">
          <Coffee size={14} strokeWidth={2.5} />
        </span>
        KORA
      </div>
      <div className="artwork-copy">
        <p className="artwork-eyebrow">
          <Sparkles size={12} /> New seasonal roast
        </p>
        <h3>{headline}</h3>
        <p>{subline}</p>
        <span className="artwork-cta">{cta}</span>
      </div>
      <div className="product-scene" aria-hidden="true">
        <span className="product-shadow" />
        <span className="product-can">
          <span className="product-can-top" />
          <span className="product-can-label">KORA</span>
          <span className="product-can-detail">COLD BREW</span>
          <span className="product-can-wave" />
        </span>
        <span className="scene-orbit orbit-one" />
        <span className="scene-orbit orbit-two" />
      </div>
      {showChrome ? (
        <div className="artwork-corner-label">AI COMPOSED · ORIGINAL LAYOUT</div>
      ) : null}
    </div>
  )
}
