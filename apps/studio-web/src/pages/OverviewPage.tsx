import {
  ArrowRight,
  Clock3,
  Download,
  ImagePlus,
  MoreHorizontal,
  MousePointerClick,
  Palette,
  Plus,
  Sparkles,
  TrendingUp,
} from 'lucide-react'
import { CreativeArtwork } from '../components/CreativeArtwork'
import { ScoreBadge } from '../components/ScoreBadge'
import { chartPoints, initialCreatives, projects } from '../data'
import type { PageId } from '../types'

interface OverviewPageProps {
  onNavigate: (page: PageId) => void
  onEdit: (creativeId: number) => void
}

export function OverviewPage({ onNavigate, onEdit }: OverviewPageProps) {
  const maxPoint = Math.max(1, ...chartPoints)
  const polylinePoints = chartPoints
    .map((point, index) => {
      const x = (index / (chartPoints.length - 1)) * 520
      const y = 150 - (point / maxPoint) * 120
      return `${x},${y}`
    })
    .join(' ')

  return (
    <div className="page overview-page">
      <section className="welcome-row">
        <div>
          <p className="eyebrow">WEDNESDAY, JULY 29</p>
          <h2>Good afternoon, Alex <span>👋</span></h2>
          <p className="page-subtitle">
            Your workspace is empty. Create your first project to start building performance history.
          </p>
        </div>
        <button
          type="button"
          className="secondary-button"
          onClick={() => onNavigate('projects')}
        >
          View all projects <ArrowRight size={15} />
        </button>
      </section>

      <section className="hero-panel">
        <div className="hero-copy">
          <div className="hero-badge">
            <Sparkles size={13} /> AI creative studio
          </div>
          <h3>Turn one product idea into a campaign.</h3>
          <p>
            Generate on-brand copy, visuals, and every ad size you need—in one
            focused workflow.
          </p>
          <div className="hero-actions">
            <button
              type="button"
              className="hero-primary"
              onClick={() => onNavigate('new-project')}
            >
              <Plus size={16} /> Create campaign
            </button>
            <button type="button" className="hero-secondary" onClick={() => onNavigate('new-project')}>
              <ImagePlus size={16} /> Upload a product
            </button>
          </div>
          <p className="hero-footnote">
            No generated assets yet
          </p>
        </div>
        <div className="hero-art">
          <div className="floating-chip chip-score">
            <TrendingUp size={14} />
            <span>Scores appear after generation</span>
          </div>
          <div className="floating-chip chip-brand">
            <Palette size={14} />
            Brand-ready
          </div>
          <CreativeArtwork
            headline="Start bright."
            subline="Slow brewed. Ready when you are."
            cta="Shop cold brew"
            variant="citrus"
            className="hero-creative"
          />
        </div>
      </section>

      <section className="metric-grid">
        <article className="metric-card">
          <div className="metric-card-head">
            <span className="metric-icon coral"><MousePointerClick size={17} /></span>
            <span className="trend neutral">No data</span>
          </div>
          <p>Avg. click-through rate</p>
          <strong>0%</strong>
          <small>Waiting for campaign data</small>
        </article>
        <article className="metric-card">
          <div className="metric-card-head">
            <span className="metric-icon violet"><Sparkles size={17} /></span>
            <span className="trend neutral">No data</span>
          </div>
          <p>Creatives generated</p>
          <strong>0</strong>
          <small>No creatives generated</small>
        </article>
        <article className="metric-card">
          <div className="metric-card-head">
            <span className="metric-icon green"><Download size={17} /></span>
            <span className="trend neutral">No data</span>
          </div>
          <p>Assets downloaded</p>
          <strong>0</strong>
          <small>No assets downloaded</small>
        </article>
        <article className="metric-card">
          <div className="metric-card-head">
            <span className="metric-icon amber"><Clock3 size={17} /></span>
            <span className="trend neutral">No data</span>
          </div>
          <p>Production time saved</p>
          <strong>0h</strong>
          <small>Calculated after generation</small>
        </article>
      </section>

      <div className="dashboard-grid">
        <section className="panel performance-panel">
          <div className="panel-header">
            <div>
              <p className="panel-kicker">Creative performance</p>
              <h3>Clicks from generated ads</h3>
            </div>
            <button type="button" className="select-button">
              Last 12 weeks <span>⌄</span>
            </button>
          </div>
          <div className="chart-summary">
            <strong>0</strong>
            <span>No performance data</span>
          </div>
          <div className="line-chart">
            <div className="chart-grid-lines">
              <span /><span /><span /><span />
            </div>
            <svg viewBox="0 0 520 160" preserveAspectRatio="none" role="img" aria-label="Clicks increased over twelve weeks">
              <defs>
                <linearGradient id="chartArea" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#7057ff" stopOpacity=".24" />
                  <stop offset="100%" stopColor="#7057ff" stopOpacity="0" />
                </linearGradient>
              </defs>
              <polygon points={`0,160 ${polylinePoints} 520,160`} fill="url(#chartArea)" />
              <polyline points={polylinePoints} fill="none" stroke="#7057ff" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
            <div className="chart-labels">
              <span>May 11</span><span>Jun 1</span><span>Jun 22</span><span>Jul 13</span>
            </div>
          </div>
        </section>

        <section className="panel activity-panel">
          <div className="panel-header">
            <div>
              <p className="panel-kicker">Workspace</p>
              <h3>Recent activity</h3>
            </div>
            <button type="button" className="icon-button"><MoreHorizontal size={18} /></button>
          </div>
          <div className="dashboard-empty compact-empty">
            <Clock3 size={19} />
            <strong>No activity yet</strong>
            <p>Project activity will appear here.</p>
          </div>
        </section>
      </div>

      <section className="content-section">
        <div className="section-title-row">
          <div>
            <p className="panel-kicker">Top performers</p>
            <h3>Creatives worth scaling</h3>
          </div>
          <button type="button" className="text-button" onClick={() => onNavigate('library')}>
            Open library <ArrowRight size={14} />
          </button>
        </div>
        <div className="creative-strip">
          {initialCreatives.length === 0 ? (
            <div className="dashboard-empty wide-empty">
              <Sparkles size={21} />
              <strong>No creatives yet</strong>
              <p>Your approved generations will appear here.</p>
              <button type="button" className="primary-button" onClick={() => onNavigate('new-project')}><Plus size={14} /> Create project</button>
            </div>
          ) : initialCreatives.slice(0, 3).map((creative) => (
            <article className="creative-card" key={creative.id}>
              <div className="creative-card-visual">
                <CreativeArtwork
                  headline={creative.headline}
                  subline={creative.subline}
                  cta={creative.cta}
                  variant={creative.variant}
                />
                <ScoreBadge score={creative.score} />
                <button
                  type="button"
                  className="creative-edit-trigger"
                  onClick={() => onEdit(creative.id)}
                >
                  Edit creative
                </button>
              </div>
              <div className="creative-card-meta">
                <div>
                  <strong>{creative.title}</strong>
                  <small>Meta · {creative.format}</small>
                </div>
                <button type="button" className="icon-button"><MoreHorizontal size={17} /></button>
              </div>
            </article>
          ))}
        </div>
      </section>

      <section className="content-section project-preview-section">
        <div className="section-title-row">
          <div>
            <p className="panel-kicker">Recent projects</p>
            <h3>Pick up where you left off</h3>
          </div>
          <button type="button" className="text-button" onClick={() => onNavigate('projects')}>
            View all projects <ArrowRight size={14} />
          </button>
        </div>
        <div className="project-list compact">
          {projects.length === 0 ? (
            <div className="dashboard-empty project-empty">
              <Sparkles size={19} />
              <strong>No projects yet</strong>
              <p>Start a project and it will be saved here.</p>
            </div>
          ) : projects.slice(0, 3).map((project) => (
            <button key={project.id} type="button" className="project-row" onClick={() => onNavigate('projects')}>
              <span className={`project-thumbnail thumb-${project.variant}`}><Sparkles size={17} /></span>
              <span className="project-main"><strong>{project.name}</strong><small>{project.type}</small></span>
              <span className="project-outputs">{project.outputs} outputs</span>
              <span className={`status-pill ${project.status.toLowerCase()}`}>{project.status}</span>
              <span className="project-date">{project.updated}</span>
              <ArrowRight size={16} />
            </button>
          ))}
        </div>
      </section>
    </div>
  )
}
