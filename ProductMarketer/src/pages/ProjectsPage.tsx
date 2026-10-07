import { useEffect, useState } from 'react'
import {
  ArrowRight,
  Filter,
  FolderKanban,
  Grid2X2,
  List,
  MoreHorizontal,
  Plus,
  Search,
  Sparkles,
} from 'lucide-react'
import { getProjects, type ProjectRecord } from '../lib/api'

interface ProjectsPageProps {
  onCreate: () => void
}

export function ProjectsPage({ onCreate }: ProjectsPageProps) {
  const [projects, setProjects] = useState<ProjectRecord[]>([])

  useEffect(() => {
    let active = true
    getProjects().then((records) => {
      if (active) setProjects(records)
    }).catch(() => undefined)
    return () => {
      active = false
    }
  }, [])

  const projectVariants = ['citrus', 'midnight', 'lavender', 'sand']

  return (
    <div className="page collection-page">
      <section className="collection-heading">
        <div>
          <p className="eyebrow">WORKSPACE</p>
          <h2>Projects</h2>
          <p className="page-subtitle">Every campaign, draft, and output in one place.</p>
        </div>
        <button type="button" className="primary-button" onClick={onCreate}>
          <Plus size={16} /> New project
        </button>
      </section>

      <section className="collection-toolbar">
        <label className="collection-search">
          <Search size={16} />
          <input placeholder="Search projects" aria-label="Search projects" />
        </label>
        <button type="button" className="toolbar-button"><Filter size={15} /> All types</button>
        <button type="button" className="toolbar-button">Last updated</button>
        <div className="toolbar-spacer" />
        <div className="view-toggle">
          <button type="button" className="active" aria-label="Grid view"><Grid2X2 size={15} /></button>
          <button type="button" aria-label="List view"><List size={16} /></button>
        </div>
      </section>

      <div className="project-card-grid">
        <button type="button" className="new-project-card" onClick={onCreate}>
          <span><Plus size={21} /></span>
          <strong>Create a new project</strong>
          <small>Start from a product, URL, or blank brief</small>
        </button>
        {projects.map((project, index) => {
          const variant = projectVariants[index % projectVariants.length]
          const displayStatus = project.status === 'ready'
            ? 'Ready'
            : project.status === 'review'
              ? 'Review'
              : project.status === 'generating' || project.status === 'processing'
                ? 'Generating'
                : 'Draft'
          return (
          <article className="project-tile" key={project.id}>
            <div className={`project-tile-visual tile-${variant}`}>
              <div className="tile-noise" />
              <span className="tile-brand">KORA</span>
              <strong>{project.title.split(' ').slice(0, 2).join(' ')}</strong>
              <span className="tile-shape"><Sparkles size={22} /></span>
              <span className="tile-output-count">{project.outputCount} outputs</span>
            </div>
            <div className="project-tile-info">
              <span className="project-type-icon"><FolderKanban size={17} /></span>
              <div>
                <strong>{project.title}</strong>
                <small>{project.category} · {new Date(project.updatedAt).toLocaleDateString()}</small>
              </div>
              <button type="button" className="icon-button"><MoreHorizontal size={17} /></button>
            </div>
            <div className="project-tile-footer">
              <span className={`status-pill ${displayStatus.toLowerCase()}`}>{displayStatus}</span>
              <button type="button">Open project <ArrowRight size={14} /></button>
            </div>
          </article>
        )})}
      </div>
    </div>
  )
}
