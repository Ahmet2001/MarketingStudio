import { useEffect, useState } from 'react'
import { Clock3, Download, MoreHorizontal, Play, Plus, Search, Sparkles } from 'lucide-react'
import { getVideos, type VideoRecord } from '../lib/api'

const videoVisuals = ['rose', 'midnight', 'lime', 'orange', 'sky', 'violet']

interface VideosPageProps {
  onCreate: () => void
}

export function VideosPage({ onCreate }: VideosPageProps) {
  const [videos, setVideos] = useState<VideoRecord[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let active = true
    getVideos()
      .then((records) => {
        if (active) setVideos(records)
      })
      .catch(() => {
        if (active) setVideos([])
      })
      .finally(() => {
        if (active) setLoading(false)
      })
    return () => {
      active = false
    }
  }, [])

  return (
    <div className="page collection-page videos-page">
      <section className="collection-heading">
        <div><p className="eyebrow">VIDEO WORKSPACE</p><h2>Generated videos</h2><p className="page-subtitle">Review, revise, and download every generated scene and final cut.</p></div>
        <button type="button" className="primary-button" onClick={onCreate}><Plus size={16} /> Create video</button>
      </section>
      <section className="video-summary-row">
        <article><span><Play size={17} /></span><div><strong>18</strong><small>Ready videos</small></div></article>
        <article><span><Clock3 size={17} /></span><div><strong>42:16</strong><small>Total generated</small></div></article>
        <article><span><Sparkles size={17} /></span><div><strong>93%</strong><small>Approval rate</small></div></article>
      </section>
      <section className="collection-toolbar">
        <label className="collection-search"><Search size={16} /><input placeholder="Search videos" aria-label="Search videos" /></label>
        <button type="button" className="toolbar-button">All video types</button>
        <button type="button" className="toolbar-button">Newest first</button>
      </section>
      <div className="video-library-grid">
        {videos.map((video, index) => {
          const visual = videoVisuals[index % videoVisuals.length]
          const displayStatus = video.status === 'ready'
            ? 'Ready'
            : video.status === 'generating' || video.status === 'processing'
              ? 'Rendering'
              : video.status === 'review'
                ? 'Review'
                : 'Draft'
          return (
          <article className="video-library-card" key={video.id}>
            <div className={`video-cover video-cover-${visual}`}>
              {video.thumbnailUrl ? <img className="video-backend-thumbnail" src={video.thumbnailUrl} alt="" /> : null}
              <span className="video-cover-brand">KORA / FILMS</span>
              <div className="video-cover-product"><i /><b>KORA</b></div>
              {index % 2 === 0 ? <span className="video-person"><i /><b /></span> : null}
              <button type="button" aria-label={`Play ${video.title}`} disabled={!video.thumbnailUrl}><Play size={17} fill="currentColor" /></button>
              <small>{video.duration}</small>
            </div>
            <div className="video-card-info">
              <div><strong>{video.title}</strong><small>{video.type} · Updated today</small></div>
              <button type="button" className="icon-button"><MoreHorizontal size={17} /></button>
            </div>
            <div className="video-card-footer">
              <span className={`video-status ${displayStatus.toLowerCase()}`}>{displayStatus === 'Rendering' ? <i /> : null}{displayStatus}</span>
              <button type="button" disabled={displayStatus !== 'Ready'}><Download size={14} /> Download</button>
            </div>
          </article>
        )})}
        {!loading && videos.length === 0 ? (
          <div className="empty-video-state"><Play size={22} /><strong>No generated videos yet</strong><p>Create your first video project to see it here.</p><button type="button" className="primary-button" onClick={onCreate}>Create video</button></div>
        ) : null}
      </div>
    </div>
  )
}
