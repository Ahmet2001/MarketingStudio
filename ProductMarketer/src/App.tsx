import { useState } from 'react'
import { CheckCircle2, X } from 'lucide-react'
import { AppHeader } from './components/AppHeader'
import { Sidebar } from './components/Sidebar'
import { CompetitorsPage } from './pages/CompetitorsPage'
import { EditorPage } from './pages/EditorPage'
import { GeneratePage } from './pages/GeneratePage'
import { InsightsPage } from './pages/InsightsPage'
import { IntegrationsPage } from './pages/IntegrationsPage'
import { LibraryPage } from './pages/LibraryPage'
import { NewProjectPage } from './pages/NewProjectPage'
import { ModelsPage } from './pages/ModelsPage'
import { OverviewPage } from './pages/OverviewPage'
import { ProfilePage } from './pages/ProfilePage'
import { ProjectsPage } from './pages/ProjectsPage'
import { SettingsPage } from './pages/SettingsPage'
import { VideosPage } from './pages/VideosPage'
import type { PageId } from './types'

const pageTitles: Record<PageId, string> = {
  overview: 'Overview',
  'new-project': 'New project',
  generate: 'Generate',
  projects: 'Projects',
  videos: 'Generated videos',
  library: 'Creative library',
  insights: 'Creative insights',
  competitors: 'Competitors',
  integrations: 'Integrations',
  models: 'AI models',
  profile: 'Profile',
  settings: 'Settings',
  editor: 'Creative editor',
}

interface ToastState {
  title: string
  message: string
}

function App() {
  const [page, setPage] = useState<PageId>('overview')
  const [previousPage, setPreviousPage] = useState<PageId>('overview')
  const [selectedCreative, setSelectedCreative] = useState(1)
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [toast, setToast] = useState<ToastState | null>(null)

  const navigate = (nextPage: PageId) => {
    if (nextPage !== 'editor') setPreviousPage(page)
    setPage(nextPage)
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  const editCreative = (creativeId: number) => {
    setSelectedCreative(creativeId)
    setPreviousPage(page)
    setPage('editor')
    window.scrollTo({ top: 0 })
  }

  const showToast = (nextToast: ToastState) => {
    setToast(nextToast)
    window.setTimeout(() => setToast(null), 3800)
  }

  const finishGeneration = () => {
    setPage('library')
    showToast({
      title: '12 creatives are ready',
      message: 'Your Kora seasonal campaign was added to the library.',
    })
  }

  const renderPage = () => {
    switch (page) {
      case 'overview':
        return <OverviewPage onNavigate={navigate} onEdit={editCreative} />
      case 'generate':
        return <GeneratePage onBack={() => navigate(previousPage)} onComplete={finishGeneration} />
      case 'new-project':
        return (
          <NewProjectPage
            onOpenClassicGenerator={() => navigate('generate')}
            onProjectCreated={(title) => {
              showToast({
                title: 'Project created',
                message: `${title} is ready in your workspace.`,
              })
            }}
          />
        )
      case 'projects':
        return <ProjectsPage onCreate={() => navigate('new-project')} />
      case 'videos':
        return <VideosPage onCreate={() => navigate('new-project')} />
      case 'library':
        return <LibraryPage onEdit={editCreative} />
      case 'insights':
        return <InsightsPage />
      case 'competitors':
        return <CompetitorsPage />
      case 'integrations':
        return <IntegrationsPage />
      case 'models':
        return <ModelsPage onSaved={(message) => showToast({ title: 'AI models updated', message })} />
      case 'profile':
        return <ProfilePage onSaved={() => showToast({ title: 'Profile updated', message: 'Your account details were saved.' })} />
      case 'settings':
        return <SettingsPage onSaved={() => showToast({ title: 'Settings saved', message: 'Your workspace preferences were updated.' })} />
      case 'editor':
        return (
          <EditorPage
            creativeId={selectedCreative}
            onBack={() => setPage(previousPage)}
            onSave={() =>
              showToast({
                title: 'Creative exported',
                message: 'Your high-resolution PNG is ready to download.',
              })
            }
          />
        )
    }
  }

  const isEditor = page === 'editor'

  return (
    <div className={`app ${isEditor ? 'editor-mode' : ''}`}>
      {isEditor ? null : (
        <Sidebar
          page={page}
          isOpen={sidebarOpen}
          onNavigate={navigate}
          onClose={() => setSidebarOpen(false)}
        />
      )}
      <div className={isEditor ? 'editor-main' : 'app-main'}>
        {isEditor ? null : (
          <AppHeader
            title={pageTitles[page]}
            onMenuClick={() => setSidebarOpen(true)}
            onGenerate={() => navigate('new-project')}
          />
        )}
        {renderPage()}
      </div>
      {toast ? (
        <div className="toast" role="status">
          <span><CheckCircle2 size={19} /></span>
          <div><strong>{toast.title}</strong><p>{toast.message}</p></div>
          <button type="button" onClick={() => setToast(null)} aria-label="Dismiss notification"><X size={15} /></button>
        </div>
      ) : null}
    </div>
  )
}

export default App
