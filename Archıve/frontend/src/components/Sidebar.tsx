import {
  CalendarClock,
  ChevronLeft,
  Cpu,
  Film,
  FolderPlus,
  Plus,
  Plug,
  Settings,
  Sparkles,
  UserRound,
  Workflow,
  X,
} from "lucide-react";
import type { ViewId } from "../types";

interface SidebarProps {
  activeView: ViewId;
  collapsed: boolean;
  mobileOpen: boolean;
  videoCount: number;
  scheduleCount: number;
  onNavigate: (view: ViewId) => void;
  onToggleCollapsed: () => void;
  onCloseMobile: () => void;
}

const navigation = [
  { id: "create" as const, label: "New project", Icon: FolderPlus },
  { id: "videos" as const, label: "Generated videos", Icon: Film },
  { id: "workflows" as const, label: "Workflows", Icon: Workflow },
  { id: "scheduler" as const, label: "Scheduler", Icon: CalendarClock },
  { id: "ai-models" as const, label: "API & models", Icon: Cpu },
  { id: "profile" as const, label: "Profile", Icon: UserRound },
  { id: "connections" as const, label: "App connections", Icon: Plug },
  { id: "settings" as const, label: "Settings", Icon: Settings },
];

export function Sidebar({
  activeView,
  collapsed,
  mobileOpen,
  videoCount,
  scheduleCount,
  onNavigate,
  onToggleCollapsed,
  onCloseMobile,
}: SidebarProps) {
  const handleNavigate = (view: ViewId) => {
    onNavigate(view);
    onCloseMobile();
  };

  return (
    <>
      <button
        className={`sidebar-backdrop ${mobileOpen ? "is-visible" : ""}`}
        type="button"
        aria-label="Close navigation"
        onClick={onCloseMobile}
      />
      <aside
        className={`sidebar ${collapsed ? "is-collapsed" : ""} ${
          mobileOpen ? "is-mobile-open" : ""
        }`}
      >
        <div className="brand-row">
          <button
            className="brand"
            type="button"
            onClick={() => handleNavigate("create")}
            aria-label="Open Storyforge home"
          >
            <span className="brand-mark">
              <Sparkles size={19} strokeWidth={2.4} />
            </span>
            <span className="brand-name">Storyforge</span>
          </button>
          <button
            className="mobile-close"
            type="button"
            aria-label="Close navigation"
            onClick={onCloseMobile}
          >
            <X size={20} />
          </button>
        </div>

        <button
          className="quick-create"
          type="button"
          onClick={() => handleNavigate("create")}
        >
          <Plus size={18} />
          <span>Create video</span>
        </button>

        <nav className="primary-nav" aria-label="Main navigation">
          <span className="nav-eyebrow">Workspace</span>
          {navigation.slice(0, 5).map(({ id, label, Icon }) => (
            <button
              className={`nav-item ${activeView === id ? "is-active" : ""}`}
              type="button"
              key={id}
              onClick={() => handleNavigate(id)}
              aria-current={activeView === id ? "page" : undefined}
            >
              <Icon size={19} strokeWidth={2} />
              <span>{label}</span>
              {id === "videos" ? (
                <span className="nav-count">{videoCount}</span>
              ) : null}
              {id === "scheduler" && scheduleCount > 0 ? (
                <span className="nav-count">{scheduleCount}</span>
              ) : null}
            </button>
          ))}

          <span className="nav-eyebrow nav-eyebrow-spaced">Account</span>
          {navigation.slice(5).map(({ id, label, Icon }) => (
            <button
              className={`nav-item ${activeView === id ? "is-active" : ""}`}
              type="button"
              key={id}
              onClick={() => handleNavigate(id)}
              aria-current={activeView === id ? "page" : undefined}
            >
              <Icon size={19} strokeWidth={2} />
              <span>{label}</span>
            </button>
          ))}
        </nav>

        <div className="sidebar-bottom">
          <div className="usage-card">
            <div className="usage-icon">
              <Sparkles size={15} />
            </div>
            <div className="usage-copy">
              <strong>12 min left</strong>
              <span>Monthly generation</span>
            </div>
            <div className="usage-bar">
              <span />
            </div>
            <button type="button">Upgrade plan</button>
          </div>

          <button
            className="collapse-button"
            type="button"
            onClick={onToggleCollapsed}
            aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
          >
            <ChevronLeft size={18} />
            <span>Collapse</span>
          </button>
        </div>
      </aside>
    </>
  );
}
