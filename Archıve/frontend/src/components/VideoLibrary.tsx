import {
  Download,
  Film,
  LoaderCircle,
  MoreHorizontal,
  Play,
  Plus,
  RotateCcw,
  Search,
  X,
} from "lucide-react";
import { useMemo, useState } from "react";
import type { VideoProject } from "../types";

interface VideoLibraryProps {
  videos: VideoProject[];
  loading: boolean;
  onCreate: () => void;
  onCancel: (projectId: string) => Promise<void>;
  onRetry: (projectId: string) => Promise<void>;
}

type StatusFilter = "All" | "Ready" | "Active" | "Failed";

export function VideoLibrary({
  videos,
  loading,
  onCreate,
  onCancel,
  onRetry,
}: VideoLibraryProps) {
  const [query, setQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("All");
  const filteredVideos = useMemo(
    () =>
      videos.filter(
        (video) =>
          video.title.toLowerCase().includes(query.trim().toLowerCase()) &&
          (statusFilter === "All" ||
            video.status === statusFilter ||
            (statusFilter === "Active" &&
              ["Queued", "Generating", "Cancelling"].includes(video.status))),
      ),
    [query, statusFilter, videos],
  );

  return (
    <section className="library-page">
      <div className="page-heading-row">
        <div>
          <span className="page-kicker">Your studio</span>
          <h1>Generated videos</h1>
          <p>Review, download, or continue every story in one place.</p>
        </div>
        <button className="primary-button" type="button" onClick={onCreate}>
          <Plus size={17} />
          New video
        </button>
      </div>

      <div className="library-toolbar">
        <label className="library-search">
          <Search size={17} />
          <span className="sr-only">Filter videos</span>
          <input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Filter your videos…"
          />
        </label>
        <div className="filter-pills">
          {(["All", "Ready", "Active", "Failed"] as const).map((status) => (
            <button
              className={statusFilter === status ? "is-active" : ""}
              type="button"
              key={status}
              onClick={() => setStatusFilter(status)}
            >
              {status}
            </button>
          ))}
        </div>
      </div>

      {loading ? (
        <div className="empty-state">
          <LoaderCircle className="spin" size={28} />
          <h2>Loading your studio</h2>
          <p>Fetching project status from the generator.</p>
        </div>
      ) : filteredVideos.length ? (
        <div className="video-grid">
          {filteredVideos.map((video) => (
            <article className="video-card" key={video.id}>
              <div className={`video-thumbnail accent-${video.accent}`}>
                <div className="video-orbit" />
                <Film size={32} />
                {["Queued", "Generating", "Cancelling"].includes(video.status) ? (
                  <div
                    className="video-progress"
                    aria-label={`${video.progress ?? 0}% generated`}
                  >
                    <span style={{ width: `${video.progress ?? 0}%` }} />
                  </div>
                ) : video.status === "Ready" && video.outputUrl ? (
                  <a
                    href={video.outputUrl}
                    target="_blank"
                    rel="noreferrer"
                    aria-label={`Play ${video.title}`}
                  >
                    <Play size={18} fill="currentColor" />
                  </a>
                ) : null}
                <span className="duration-label">{video.duration}</span>
              </div>
              <div className="video-card-copy">
                <div className="video-title-row">
                  <h2>{video.title}</h2>
                  <button type="button" aria-label={`More options for ${video.title}`}>
                    <MoreHorizontal size={19} />
                  </button>
                </div>
                <span>{video.mode}</span>
                <p className="video-stage">
                  {video.error ?? video.stage}
                </p>
                <div className="video-card-footer">
                  <span
                    className={`status status-${video.status.toLowerCase()}`}
                  >
                    {video.status}
                  </span>
                  <span>{video.date}</span>
                  {video.status === "Ready" && video.outputUrl ? (
                    <a
                      href={video.outputUrl}
                      download
                      aria-label={`Download ${video.title}`}
                    >
                      <Download size={16} />
                    </a>
                  ) : null}
                  {["Queued", "Generating"].includes(video.status) ? (
                    <button
                      type="button"
                      onClick={() => void onCancel(video.id)}
                      aria-label={`Cancel ${video.title}`}
                      title="Cancel generation"
                    >
                      <X size={16} />
                    </button>
                  ) : null}
                  {["Failed", "Cancelled"].includes(video.status) ? (
                    <button
                      type="button"
                      onClick={() => void onRetry(video.id)}
                      aria-label={`Retry ${video.title}`}
                      title="Retry generation"
                    >
                      <RotateCcw size={16} />
                    </button>
                  ) : null}
                </div>
              </div>
            </article>
          ))}
        </div>
      ) : (
        <div className="empty-state">
          {videos.length ? <Search size={28} /> : <Film size={28} />}
          <h2>
            {videos.length ? `No videos match “${query}”` : "Your studio is empty"}
          </h2>
          <p>
            {videos.length
              ? "Try another title or change the status filter."
              : "Choose a creation mode and generate your first video."}
          </p>
          {!videos.length ? (
            <button className="secondary-button" type="button" onClick={onCreate}>
              <Plus size={16} />
              Create first video
            </button>
          ) : null}
        </div>
      )}
    </section>
  );
}
