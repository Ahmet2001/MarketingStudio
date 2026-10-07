import { ArrowUpRight, Check } from "lucide-react";
import type { ProjectMode } from "../types";

interface ProjectCardProps {
  mode: ProjectMode;
  featured?: boolean;
  onSelect: (mode: ProjectMode) => void;
}

function CardArtwork({ mode }: { mode: ProjectMode }) {
  const { Icon, accent, id } = mode;

  return (
    <div className={`card-art card-art-${accent}`} aria-hidden="true">
      <div className="art-glow" />
      {id === "reddit" ? (
        <>
          <div className="phone-caption">
            <span>STORY TIME</span>
            <strong>“I thought the door was locked…”</strong>
          </div>
          <div className="game-block game-block-one" />
          <div className="game-block game-block-two" />
        </>
      ) : null}
      {id === "ai-photos" ? (
        <>
          <div className="portrait silhouette-one" />
          <div className="portrait silhouette-two" />
          <span className="art-caption">ONE IDEA · FOUR SCENES</span>
        </>
      ) : null}
      {id === "real-images" || id === "documentary" ? (
        <>
          <div className="archive-photo">
            <span>{id === "documentary" ? "ARCHIVE / 1969" : "TRUE STORY"}</span>
          </div>
          <div className="archive-tape" />
        </>
      ) : null}
      {id === "stock-explainer" ? (
        <>
          <div className="stock-frame stock-frame-one" />
          <div className="stock-frame stock-frame-two" />
          <div className="stock-copy">HOW IT WORKS</div>
        </>
      ) : null}
      {id === "avatar" ? (
        <>
          <div className="avatar-head" />
          <div className="avatar-body" />
          <div className="sound-wave">
            <i />
            <i />
            <i />
            <i />
          </div>
        </>
      ) : null}
      <span className="art-icon">
        <Icon size={18} />
      </span>
    </div>
  );
}

export function ProjectCard({
  mode,
  featured = false,
  onSelect,
}: ProjectCardProps) {
  return (
    <article
      className={`project-card ${featured ? "is-featured" : ""} ${
        mode.available ? "" : "is-unavailable"
      }`}
      data-accent={mode.accent}
    >
      <button
        className="project-card-button"
        type="button"
        onClick={() => {
          if (mode.available) onSelect(mode);
        }}
        disabled={!mode.available}
        aria-label={`Create ${mode.title}`}
      >
        <CardArtwork mode={mode} />
        <div className="project-card-copy">
          <div className="project-card-meta">
            <span className="engine-label">
              <Check size={12} />
              {mode.engine}
            </span>
            {mode.badge ? <span className="mode-badge">{mode.badge}</span> : null}
          </div>
          <div className="project-card-title-row">
            <h3>{mode.title}</h3>
            <span className="card-arrow">
              {mode.available ? <ArrowUpRight size={18} /> : <Check size={16} />}
            </span>
          </div>
          <p>{mode.description}</p>
          <div className="example-chips" aria-label="Example formats">
            {mode.examples.map((example) => (
              <span key={example}>{example}</span>
            ))}
          </div>
        </div>
      </button>
    </article>
  );
}
