import {
  BarChart3,
  Blocks,
  ChevronDown,
  CircleUserRound,
  Clapperboard,
  Cpu,
  FolderKanban,
  GalleryVerticalEnd,
  LayoutDashboard,
  Link2,
  Plus,
  Search,
  Settings,
  X,
} from 'lucide-react'
import { LogoMark } from './LogoMark'
import type { PageId } from '../types'

const primaryNavigation: Array<{
  id: PageId
  label: string
  icon: typeof LayoutDashboard
  tag?: string
}> = [
  { id: 'overview', label: 'Overview', icon: LayoutDashboard },
  { id: 'new-project', label: 'New project', icon: Plus, tag: 'CREATE' },
  { id: 'projects', label: 'Projects', icon: FolderKanban },
  { id: 'videos', label: 'Generated videos', icon: Clapperboard },
  { id: 'library', label: 'Creative library', icon: GalleryVerticalEnd },
]

const intelligenceNavigation: Array<{
  id: PageId
  label: string
  icon: typeof LayoutDashboard
}> = [
  { id: 'insights', label: 'Creative insights', icon: BarChart3 },
  { id: 'competitors', label: 'Competitors', icon: Search },
  { id: 'integrations', label: 'Integrations', icon: Link2 },
  { id: 'models', label: 'AI models', icon: Cpu },
]

const accountNavigation: Array<{
  id: PageId
  label: string
  icon: typeof LayoutDashboard
}> = [
  { id: 'profile', label: 'Profile', icon: CircleUserRound },
  { id: 'settings', label: 'Settings', icon: Settings },
]

interface SidebarProps {
  page: PageId
  isOpen: boolean
  onNavigate: (page: PageId) => void
  onClose: () => void
}

export function Sidebar({
  page,
  isOpen,
  onNavigate,
  onClose,
}: SidebarProps) {
  const renderButton = ({
    id,
    label,
    icon: Icon,
    tag,
  }: (typeof primaryNavigation)[number]) => (
    <button
      key={id}
      type="button"
      className={`nav-item ${page === id ? 'active' : ''}`}
      onClick={() => {
        onNavigate(id)
        onClose()
      }}
    >
      <Icon size={18} strokeWidth={1.8} />
      <span>{label}</span>
      {tag ? <em>{tag}</em> : null}
    </button>
  )

  return (
    <>
      <div
        className={`sidebar-overlay ${isOpen ? 'visible' : ''}`}
        onClick={onClose}
        aria-hidden="true"
      />
      <aside className={`sidebar ${isOpen ? 'open' : ''}`}>
        <div className="sidebar-top">
          <LogoMark />
          <button
            type="button"
            className="icon-button sidebar-close"
            onClick={onClose}
            aria-label="Close navigation"
          >
            <X size={18} />
          </button>
        </div>

        <button className="workspace-switcher" type="button">
          <span className="workspace-avatar">K</span>
          <span className="workspace-copy">
            <strong>Kora Coffee</strong>
            <small>Professional plan</small>
          </span>
          <ChevronDown size={16} />
        </button>

        <nav className="sidebar-nav" aria-label="Main navigation">
          <div className="nav-group">
            <p>Workspace</p>
            {primaryNavigation.map(renderButton)}
          </div>
          <div className="nav-group">
            <p>Intelligence</p>
            {intelligenceNavigation.map(renderButton)}
          </div>
          <div className="nav-group account-nav-group">
            <p>Account</p>
            {accountNavigation.map(renderButton)}
          </div>
        </nav>

        <div className="sidebar-bottom">
          <div className="upgrade-card">
            <div className="upgrade-icon">
              <Blocks size={17} />
            </div>
            <strong>Unlock brand memory</strong>
            <p>Train ProductMarketer on your winning ads.</p>
            <button type="button">Explore Pro</button>
          </div>
          <button type="button" className="account-row" onClick={() => onNavigate('profile')}>
            <CircleUserRound size={30} strokeWidth={1.5} />
            <span>
              <strong>Alex Morgan</strong>
              <small>alex@kora.co</small>
            </span>
            <Settings size={16} />
          </button>
        </div>
      </aside>
    </>
  )
}
