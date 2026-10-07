import {
  BarChart3,
  ChevronDown,
  Eye,
  Link2,
  MousePointerClick,
  RefreshCcw,
  Sparkles,
  TrendingUp,
} from 'lucide-react'

export function InsightsPage() {
  return (
    <div className="page insights-page">
      <section className="collection-heading">
        <div>
          <p className="eyebrow">CREATIVE INTELLIGENCE</p>
          <h2>Performance insights</h2>
          <p className="page-subtitle">Performance appears after you connect an ad account and publish creatives.</p>
        </div>
        <div className="heading-actions">
          <button type="button" className="secondary-button" disabled><RefreshCcw size={14} /> Sync data</button>
          <button type="button" className="select-button">Last 30 days <ChevronDown size={14} /></button>
        </div>
      </section>

      <section className="connected-account-bar empty-account-bar">
        <span className="meta-account-icon"><Link2 size={15} /></span>
        <div><strong>No ad account connected</strong><small>Connect Meta, Google, or TikTok Ads to import performance.</small></div>
        <button type="button">Connect account</button>
      </section>

      <section className="insight-metrics">
        <article>
          <span className="metric-icon coral"><Eye size={17} /></span>
          <p>Impressions</p>
          <strong>0</strong>
          <small>No data</small>
        </article>
        <article>
          <span className="metric-icon violet"><MousePointerClick size={17} /></span>
          <p>Click-through rate</p>
          <strong>0%</strong>
          <small>No data</small>
        </article>
        <article>
          <span className="metric-icon green"><TrendingUp size={17} /></span>
          <p>Return on ad spend</p>
          <strong>0×</strong>
          <small>No data</small>
        </article>
        <article>
          <span className="metric-icon amber"><Sparkles size={17} /></span>
          <p>Creative fatigue</p>
          <strong>—</strong>
          <small>No data</small>
        </article>
      </section>

      <section className="insights-empty-state">
        <span><BarChart3 size={26} /></span>
        <h3>No performance data yet</h3>
        <p>Connect an advertising account and publish your first creative. ProductMarketer will then surface trends, comparisons, and recommendations here.</p>
        <button type="button" className="primary-button"><Link2 size={15} /> Connect ad account</button>
      </section>
    </div>
  )
}
