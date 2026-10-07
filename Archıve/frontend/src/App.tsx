import { useCallback, useEffect, useState } from "react";
import { Check, CloudOff, LoaderCircle, Sparkles } from "lucide-react";
import {
  cancelSchedule,
  cancelProject,
  connectApp,
  createProject,
  createSchedule,
  deleteAiModel,
  disconnectApp,
  listAiModels,
  listAiProviders,
  listConnections,
  listProjects,
  listSchedules,
  retryProject,
  removeAiProviderKey,
  runScheduleNow,
  saveAiModel,
  saveAiProviderKey,
  startProject,
} from "./api";
import { AiModelsPage } from "./components/AiModelsPage";
import { ConnectionsPage } from "./components/ConnectionsPage";
import { Header } from "./components/Header";
import { ProfilePage, SettingsPage } from "./components/AccountPages";
import { CreatePanel } from "./components/CreatePanel";
import { ProjectCard } from "./components/ProjectCard";
import { Sidebar } from "./components/Sidebar";
import { SchedulerPage } from "./components/SchedulerPage";
import { VideoLibrary } from "./components/VideoLibrary";
import { WorkflowPage } from "./components/WorkflowPage";
import { projectModes } from "./data";
import type {
  AiModel,
  AiProvider,
  AiProviderId,
  AppConnection,
  CreateProjectOptions,
  ProjectMode,
  ScheduledProject,
  VideoProject,
  ViewId,
  WorkflowRun,
} from "./types";

export default function App() {
  const [activeView, setActiveView] = useState<ViewId>("create");
  const [selectedMode, setSelectedMode] = useState<ProjectMode | null>(null);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [videos, setVideos] = useState<VideoProject[]>([]);
  const [projectsLoading, setProjectsLoading] = useState(true);
  const [schedules, setSchedules] = useState<ScheduledProject[]>([]);
  const [schedulesLoading, setSchedulesLoading] = useState(true);
  const [connections, setConnections] = useState<AppConnection[]>([]);
  const [connectionsLoading, setConnectionsLoading] = useState(true);
  const [aiProviders, setAiProviders] = useState<AiProvider[]>([]);
  const [aiModels, setAiModels] = useState<AiModel[]>([]);
  const [aiSettingsLoading, setAiSettingsLoading] = useState(true);
  const [apiConnected, setApiConnected] = useState(true);
  const [toast, setToast] = useState("");

  const refreshProjects = useCallback(async (signal?: AbortSignal) => {
    try {
      const projects = await listProjects(signal);
      setVideos(projects);
      setApiConnected(true);
    } catch (error) {
      if (error instanceof DOMException && error.name === "AbortError") return;
      setApiConnected(false);
    } finally {
      if (!signal?.aborted) setProjectsLoading(false);
    }
  }, []);

  const refreshSchedules = useCallback(async (signal?: AbortSignal) => {
    try {
      setSchedules(await listSchedules(signal));
    } catch (error) {
      if (error instanceof DOMException && error.name === "AbortError") return;
    } finally {
      if (!signal?.aborted) setSchedulesLoading(false);
    }
  }, []);

  const refreshConnections = useCallback(async (signal?: AbortSignal) => {
    try {
      setConnections(await listConnections(signal));
    } catch (error) {
      if (error instanceof DOMException && error.name === "AbortError") return;
    } finally {
      if (!signal?.aborted) setConnectionsLoading(false);
    }
  }, []);

  const refreshAiSettings = useCallback(async (signal?: AbortSignal) => {
    try {
      const [providers, models] = await Promise.all([
        listAiProviders(signal),
        listAiModels(signal),
      ]);
      setAiProviders(providers);
      setAiModels(models);
    } catch (error) {
      if (error instanceof DOMException && error.name === "AbortError") return;
    } finally {
      if (!signal?.aborted) setAiSettingsLoading(false);
    }
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    void Promise.all([
      refreshProjects(controller.signal),
      refreshSchedules(controller.signal),
      refreshConnections(controller.signal),
      refreshAiSettings(controller.signal),
    ]);
    return () => controller.abort();
  }, [
    refreshAiSettings,
    refreshConnections,
    refreshProjects,
    refreshSchedules,
  ]);

  useEffect(() => {
    const handleConnectionMessage = (event: MessageEvent) => {
      if (
        event.data?.type === "storyforge:connection" &&
        ["youtube", "tiktok", "instagram"].includes(event.data?.provider)
      ) {
        void refreshConnections();
      }
    };
    window.addEventListener("message", handleConnectionMessage);
    return () => window.removeEventListener("message", handleConnectionMessage);
  }, [refreshConnections]);

  const hasActiveProjects = videos.some((video) =>
    ["Queued", "Generating", "Cancelling"].includes(video.status),
  );
  const hasPendingSchedules = schedules.some((schedule) =>
    ["Scheduled", "Dispatching"].includes(schedule.status),
  );

  useEffect(() => {
    if (!hasActiveProjects || !apiConnected) return;
    const intervalId = window.setInterval(() => {
      void refreshProjects();
    }, 2000);
    return () => window.clearInterval(intervalId);
  }, [apiConnected, hasActiveProjects, refreshProjects]);

  useEffect(() => {
    if (!hasPendingSchedules || !apiConnected) return;
    const intervalId = window.setInterval(() => {
      void Promise.all([refreshSchedules(), refreshProjects()]);
    }, 5000);
    return () => window.clearInterval(intervalId);
  }, [
    apiConnected,
    hasPendingSchedules,
    refreshProjects,
    refreshSchedules,
  ]);

  useEffect(() => {
    if (!toast) return;
    const timeoutId = window.setTimeout(() => setToast(""), 3200);
    return () => window.clearTimeout(timeoutId);
  }, [toast]);

  const navigate = (view: ViewId) => {
    setActiveView(view);
    if (view !== "create") setSelectedMode(null);
  };

  const handleCreate = async (options: CreateProjectOptions) => {
    if (!selectedMode) return;
    const draft = await createProject(selectedMode.id, options);
    setVideos((current) => [draft, ...current]);
    const queued = await startProject(draft.id);
    setVideos((current) =>
      current.map((video) => (video.id === queued.id ? queued : video)),
    );
    setApiConnected(true);
    setToast("Project added to your generation queue");
    setSelectedMode(null);
    setActiveView("videos");
  };

  const handleScheduleCreate = async (
    options: CreateProjectOptions,
    runAt: string,
  ) => {
    if (!selectedMode) return;
    const draft = await createProject(selectedMode.id, options);
    const scheduled = await createSchedule(draft.id, runAt);
    setVideos((current) => [draft, ...current]);
    setSchedules((current) => [scheduled, ...current]);
    setToast("Video scheduled successfully");
    setSelectedMode(null);
    setActiveView("scheduler");
  };

  const handleCancel = async (projectId: string) => {
    try {
      const project = await cancelProject(projectId);
      setVideos((current) =>
        current.map((video) => (video.id === project.id ? project : video)),
      );
      setToast("Generation is stopping safely");
    } catch (error) {
      setToast(error instanceof Error ? error.message : "Could not cancel project");
    }
  };

  const handleRetry = async (projectId: string) => {
    try {
      const project = await retryProject(projectId);
      setVideos((current) =>
        current.map((video) => (video.id === project.id ? project : video)),
      );
      setToast("Project returned to the generation queue");
    } catch (error) {
      setToast(error instanceof Error ? error.message : "Could not retry project");
    }
  };

  const handleCancelSchedule = async (scheduleId: string) => {
    try {
      const schedule = await cancelSchedule(scheduleId);
      setSchedules((current) =>
        current.map((item) => (item.id === schedule.id ? schedule : item)),
      );
      setToast("Schedule cancelled");
    } catch (error) {
      setToast(error instanceof Error ? error.message : "Could not cancel schedule");
    }
  };

  const handleRunSchedule = async (scheduleId: string) => {
    try {
      const schedule = await runScheduleNow(scheduleId);
      setSchedules((current) =>
        current.map((item) => (item.id === schedule.id ? schedule : item)),
      );
      await refreshProjects();
      setToast("Scheduled video sent to the generator");
    } catch (error) {
      setToast(error instanceof Error ? error.message : "Could not run schedule");
    }
  };

  const handleConnect = async (provider: AppConnection["provider"]) => {
    try {
      const result = await connectApp(provider);
      if (result.connection) {
        setConnections((current) =>
          current.map((item) =>
            item.provider === provider ? result.connection! : item,
          ),
        );
        setToast(`${result.connection.name} connected`);
      } else if (result.authorizationUrl) {
        window.open(
          result.authorizationUrl,
          "storyforge-oauth",
          "width=620,height=760",
        );
      }
    } catch (error) {
      setToast(error instanceof Error ? error.message : "Could not connect app");
    }
  };

  const handleDisconnect = async (provider: AppConnection["provider"]) => {
    try {
      const connection = await disconnectApp(provider);
      setConnections((current) =>
        current.map((item) =>
          item.provider === provider ? connection : item,
        ),
      );
      setToast(`${connection.name} disconnected`);
    } catch (error) {
      setToast(error instanceof Error ? error.message : "Could not disconnect app");
    }
  };

  const handleSaveAiKey = async (provider: AiProviderId, apiKey: string) => {
    const updated = await saveAiProviderKey(provider, apiKey);
    setAiProviders((current) =>
      current.map((item) => (item.provider === provider ? updated : item)),
    );
    setToast(`${updated.name} API key saved securely`);
  };

  const handleRemoveAiKey = async (provider: AiProviderId) => {
    const updated = await removeAiProviderKey(provider);
    setAiProviders((current) =>
      current.map((item) => (item.provider === provider ? updated : item)),
    );
    setToast(`${updated.name} API key removed`);
  };

  const handleSaveAiModel = async (model: AiModel) => {
    const saved = await saveAiModel(model);
    setAiModels((current) => {
      const exists = current.some((item) => item.id === saved.id);
      const next = exists
        ? current.map((item) => (item.id === saved.id ? saved : item))
        : [saved, ...current];
      return saved.isDefault
        ? next.map((item) =>
            item.id === saved.id ? item : { ...item, isDefault: false },
          )
        : next;
    });
    setToast(`${saved.name} saved to your model list`);
  };

  const handleDeleteAiModel = async (modelId: string) => {
    await deleteAiModel(modelId);
    setAiModels((current) => current.filter((item) => item.id !== modelId));
    setToast("Model removed");
  };

  const handleWorkflowRun = async (run: WorkflowRun) => {
    await Promise.all([refreshProjects(), refreshSchedules()]);
    setToast(
      run.status === "scheduled"
        ? "Workflow saved and scheduled"
        : "Workflow sent to the generation queue",
    );
  };

  return (
    <div className={`app-shell ${sidebarCollapsed ? "sidebar-collapsed" : ""}`}>
      <Sidebar
        activeView={activeView}
        collapsed={sidebarCollapsed}
        mobileOpen={mobileOpen}
        videoCount={videos.length}
        scheduleCount={
          schedules.filter((schedule) => schedule.status === "Scheduled").length
        }
        onNavigate={navigate}
        onToggleCollapsed={() => setSidebarCollapsed((value) => !value)}
        onCloseMobile={() => setMobileOpen(false)}
      />
      <div className="app-main">
        <Header
          view={activeView}
          onOpenMenu={() => setMobileOpen(true)}
          onNavigateProfile={() => navigate("profile")}
        />
        <main>
          {!apiConnected ? (
            <div className="service-banner" role="status">
              <CloudOff size={17} />
              <span>
                <strong>Generator API is offline.</strong>
                Start the API and worker to create or refresh projects.
              </span>
              <button type="button" onClick={() => void refreshProjects()}>
                Reconnect
              </button>
            </div>
          ) : null}
          {activeView === "create" && !selectedMode ? (
            <section className="create-page">
              <div className="create-intro">
                <div>
                  <span className="page-kicker">
                    <Sparkles size={14} />
                    AI video studio
                  </span>
                  <h1>What will you create today?</h1>
                  <p>
                    Choose a format. Storyforge handles the research, visuals,
                    narration, captions, and final cut.
                  </p>
                </div>
                <div className="pipeline-chip">
                  <span className="pipeline-dot" />
                  <div>
                  <strong>All systems ready</strong>
                    <small>
                      {apiConnected
                        ? "2 creation engines connected"
                        : "Waiting for generator API"}
                    </small>
                  </div>
                </div>
              </div>

              <div className="mode-grid">
                {projectModes.map((mode, index) => (
                  <ProjectCard
                    key={mode.id}
                    mode={mode}
                    featured={index < 3}
                    onSelect={setSelectedMode}
                  />
                ))}
              </div>

              <div className="trust-strip">
                <span>
                  <Check size={15} /> Research-grounded scripts
                </span>
                <span>
                  <Check size={15} /> Natural AI narration
                </span>
                <span>
                  <Check size={15} /> 9:16 captions included
                </span>
                <span>
                  <Check size={15} /> Editable project files
                </span>
              </div>
            </section>
          ) : null}

          {activeView === "create" && selectedMode ? (
            <CreatePanel
              mode={selectedMode}
              aiModels={aiModels}
              aiProviders={aiProviders}
              onBack={() => setSelectedMode(null)}
              onOpenAiModels={() => navigate("ai-models")}
              onCreate={handleCreate}
              onSchedule={handleScheduleCreate}
            />
          ) : null}

          {activeView === "videos" ? (
            <VideoLibrary
              videos={videos}
              loading={projectsLoading}
              onCreate={() => navigate("create")}
              onCancel={handleCancel}
              onRetry={handleRetry}
            />
          ) : null}
          {activeView === "scheduler" ? (
            <SchedulerPage
              schedules={schedules}
              loading={schedulesLoading}
              onCreate={() => navigate("create")}
              onCancel={handleCancelSchedule}
              onRunNow={handleRunSchedule}
            />
          ) : null}
          {activeView === "workflows" ? (
            <WorkflowPage
              connections={connections}
              onNavigateConnections={() => navigate("connections")}
              onRunComplete={(run) => void handleWorkflowRun(run)}
              onNotify={setToast}
            />
          ) : null}
          {activeView === "connections" ? (
            <ConnectionsPage
              connections={connections}
              loading={connectionsLoading}
              onConnect={handleConnect}
              onDisconnect={handleDisconnect}
            />
          ) : null}
          {activeView === "ai-models" ? (
            <AiModelsPage
              providers={aiProviders}
              models={aiModels}
              loading={aiSettingsLoading}
              onSaveKey={handleSaveAiKey}
              onRemoveKey={handleRemoveAiKey}
              onSaveModel={handleSaveAiModel}
              onDeleteModel={handleDeleteAiModel}
            />
          ) : null}
          {activeView === "profile" ? <ProfilePage /> : null}
          {activeView === "settings" ? <SettingsPage /> : null}
        </main>
      </div>

      <div className={`toast ${toast ? "is-visible" : ""}`} role="status">
        <span>
          {projectsLoading ? (
            <LoaderCircle className="spin" size={16} />
          ) : (
            <Check size={16} />
          )}
        </span>
        {toast}
      </div>
    </div>
  );
}
