import { ArrowRight, Globe2, Plus, Search } from 'lucide-react'

export function CompetitorsPage() {
  return (
    <div className="page collection-page">
      <section className="collection-heading">
        <div><p className="eyebrow">MARKET INTELLIGENCE</p><h2>Competitors</h2><p className="page-subtitle">Track creative patterns and find your next campaign angle.</p></div>
        <button type="button" className="primary-button"><Plus size={16} /> Track competitor</button>
      </section>
      <section className="competitor-search-hero">
        <div><span><Search size={19} /></span><div><strong>Analyze any brand</strong><p>Enter a website to uncover messaging, channels, and creative patterns.</p></div></div>
        <label><Globe2 size={16} /><input placeholder="competitor.com" /><button type="button">Analyze <ArrowRight size={15} /></button></label>
      </section>
      <div className="competitor-grid">
        <div className="empty-competitors">
          <Search size={23} />
          <strong>No competitors tracked</strong>
          <p>Add a competitor domain to begin collecting market intelligence.</p>
          <button type="button" className="primary-button"><Plus size={14} /> Track competitor</button>
        </div>
      </div>
    </div>
  )
}
