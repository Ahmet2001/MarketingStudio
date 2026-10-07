import {
  Bell,
  ChevronDown,
  Command,
  Menu,
  Search,
  Sparkles,
} from 'lucide-react'
import { LogoMark } from './LogoMark'

interface AppHeaderProps {
  title: string
  onMenuClick: () => void
  onGenerate: () => void
}

export function AppHeader({
  title,
  onMenuClick,
  onGenerate,
}: AppHeaderProps) {
  return (
    <header className="app-header">
      <div className="mobile-logo">
        <LogoMark compact />
      </div>
      <button
        className="icon-button mobile-menu"
        type="button"
        onClick={onMenuClick}
        aria-label="Open navigation"
      >
        <Menu size={20} />
      </button>
      <div className="header-title">
        <h1>{title}</h1>
      </div>
      <div className="header-actions">
        <button type="button" className="search-trigger">
          <Search size={16} />
          <span>Search anything</span>
          <kbd>
            <Command size={11} /> K
          </kbd>
        </button>
        <button type="button" className="credit-pill">
          <span>
            <Sparkles size={13} fill="currentColor" />
          </span>
          <strong>0</strong>
          <small>credits</small>
          <ChevronDown size={14} />
        </button>
        <button
          type="button"
          className="icon-button notification-button"
          aria-label="Notifications"
        >
          <Bell size={18} />
          <span />
        </button>
        <button type="button" className="primary-button header-generate" onClick={onGenerate}>
          <Sparkles size={15} />
          Generate
        </button>
      </div>
    </header>
  )
}
