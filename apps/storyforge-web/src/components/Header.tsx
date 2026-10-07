import { Bell, Menu, Search } from "lucide-react";
import type { ViewId } from "../types";

const viewLabels: Record<ViewId, string> = {
  create: "Create",
  videos: "Generated videos",
  workflows: "Workflows",
  scheduler: "Scheduler",
  "ai-models": "API & models",
  connections: "App connections",
  profile: "Profile",
  settings: "Settings",
};

interface HeaderProps {
  view: ViewId;
  onOpenMenu: () => void;
  onNavigateProfile: () => void;
}

export function Header({
  view,
  onOpenMenu,
  onNavigateProfile,
}: HeaderProps) {
  return (
    <header className="topbar">
      <div className="topbar-left">
        <button
          className="menu-button"
          type="button"
          onClick={onOpenMenu}
          aria-label="Open navigation"
        >
          <Menu size={21} />
        </button>
        <span className="current-view">{viewLabels[view]}</span>
      </div>
      <div className="topbar-actions">
        <label className="search-box">
          <Search size={17} />
          <span className="sr-only">Search projects</span>
          <input type="search" placeholder="Search projects" />
          <kbd>⌘ K</kbd>
        </label>
        <button
          className="icon-button notification-button"
          type="button"
          aria-label="Notifications"
        >
          <Bell size={19} />
          <span />
        </button>
        <button
          className="avatar-button"
          type="button"
          onClick={onNavigateProfile}
          aria-label="Open profile"
        >
          RA
        </button>
      </div>
    </header>
  );
}
