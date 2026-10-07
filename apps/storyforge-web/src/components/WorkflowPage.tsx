import {
  CalendarClock,
  Check,
  ChevronRight,
  CirclePlus,
  Clock3,
  ExternalLink,
  LoaderCircle,
  Play,
  Plug,
  Save,
  Sparkles,
  Workflow as WorkflowIcon,
  Youtube,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import {
  listWorkflows,
  runWorkflow,
  saveWorkflow,
} from "../api";
import { projectModes } from "../data";
import type {
  AppConnection,
  Workflow,
  WorkflowNode,
  WorkflowRun,
} from "../types";
import { WorkflowNodeCard } from "./WorkflowNodeCard";

interface WorkflowPageProps {
  connections: AppConnection[];
  onNavigateConnections: () => void;
  onRunComplete: (run: WorkflowRun) => void;
  onNotify: (message: string) => void;
}

const CANVAS_WIDTH = 1040;
const CANVAS_HEIGHT = 540;
const NODE_WIDTH = 214;
const NODE_HEIGHT = 104;

const destinationOptions = [
  { id: "youtube", label: "YouTube", available: true },
  { id: "tiktok", label: "TikTok", available: true },
  { id: "instagram", label: "Instagram", available: false },
] as const;

function uniqueId(prefix: string): string {
  return `${prefix}-${crypto.randomUUID()}`;
}

function starterWorkflow(): Workflow {
  const generatorId = uniqueId("generator");
  const schedulerId = uniqueId("scheduler");
  return {
    name: "My first content automation",
    status: "draft",
    nodes: [
      {
        id: generatorId,
        kind: "content-generator",
        subtype: "ai-photos",
        label: "Storyteller with AI photos",
        x: 80,
        y: 190,
        config: {
          topic: "",
          duration: 45,
          scenes: 7,
          language: "English",
          niche: "general-storytelling",
        },
      },
      {
        id: schedulerId,
        kind: "scheduler",
        subtype: "delay",
        label: "Schedule",
        x: 400,
        y: 190,
        config: {
          delay_minutes: 5,
          timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
        },
      },
    ],
    edges: [
      {
        id: uniqueId("edge"),
        source: generatorId,
        target: schedulerId,
      },
    ],
  };
}

function formatLastRun(value?: string): string {
  if (!value) return "Never";
  return new Date(value).toLocaleString([], {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function nodeDetail(node: WorkflowNode): string {
  if (node.kind === "content-generator") {
    return node.config.topic?.trim() || "AI idea on every run";
  }
  if (node.kind === "scheduler") {
    return `Wait ${node.config.delay_minutes ?? 5} minutes`;
  }
  return "Publishing destination";
}

export function WorkflowPage({
  connections,
  onNavigateConnections,
  onRunComplete,
  onNotify,
}: WorkflowPageProps) {
  const [workflows, setWorkflows] = useState<Workflow[]>([]);
  const [workflow, setWorkflow] = useState<Workflow>(() => starterWorkflow());
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(
    () => workflow.nodes[0]?.id ?? null,
  );
  const [pendingSourceId, setPendingSourceId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [running, setRunning] = useState(false);
  const [dirty, setDirty] = useState(true);
  const [statusMessage, setStatusMessage] = useState(
    "Connect nodes from left to right, then run the automation.",
  );

  useEffect(() => {
    let ignore = false;
    const load = async () => {
      try {
        const items = await listWorkflows();
        if (!ignore) setWorkflows(items);
      } catch (error) {
        if (!ignore) {
          setStatusMessage(
            error instanceof Error
              ? error.message
              : "Could not load saved workflows.",
          );
        }
      } finally {
        if (!ignore) setLoading(false);
      }
    };
    void load();
    return () => {
      ignore = true;
    };
  }, []);

  const selectedNode = useMemo(
    () => workflow.nodes.find((node) => node.id === selectedNodeId) ?? null,
    [selectedNodeId, workflow.nodes],
  );
  const nodesById = useMemo(
    () => new Map(workflow.nodes.map((node) => [node.id, node])),
    [workflow.nodes],
  );

  const changeWorkflow = (updater: (current: Workflow) => Workflow) => {
    setWorkflow(updater);
    setDirty(true);
  };

  const addNode = (
    kind: WorkflowNode["kind"],
    subtype: string,
    label: string,
  ) => {
    const existing = workflow.nodes.find((node) => node.kind === kind);
    if (existing) {
      changeWorkflow((current) => ({
        ...current,
        nodes: current.nodes.map((node) =>
          node.id === existing.id
            ? {
                ...node,
                subtype,
                label,
                config:
                  kind === "content-generator"
                    ? {
                        topic: "",
                        duration: 45,
                        scenes: 7,
                        language: "English",
                        niche: "general-storytelling",
                      }
                    : node.config,
              }
            : node,
        ),
      }));
      setSelectedNodeId(existing.id);
      return;
    }

    const index = workflow.nodes.length;
    const node: WorkflowNode = {
      id: uniqueId(kind),
      kind,
      subtype,
      label,
      x: Math.min(760, 80 + index * 260),
      y: 105 + (index % 3) * 130,
      config:
        kind === "scheduler"
          ? {
              delay_minutes: 5,
              timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
            }
          : kind === "content-generator"
            ? {
                topic: "",
                duration: 45,
                scenes: 7,
                language: "English",
                niche: "general-storytelling",
              }
            : {},
    };
    changeWorkflow((current) => ({
      ...current,
      nodes: [...current.nodes, node],
    }));
    setSelectedNodeId(node.id);
  };

  const moveNode = (nodeId: string, deltaX: number, deltaY: number) => {
    changeWorkflow((current) => ({
      ...current,
      nodes: current.nodes.map((node) =>
        node.id === nodeId
          ? {
              ...node,
              x: Math.max(
                12,
                Math.min(CANVAS_WIDTH - NODE_WIDTH - 12, node.x + deltaX),
              ),
              y: Math.max(
                54,
                Math.min(CANVAS_HEIGHT - NODE_HEIGHT - 12, node.y + deltaY),
              ),
            }
          : node,
      ),
    }));
  };

  const removeNode = (nodeId: string) => {
    changeWorkflow((current) => ({
      ...current,
      nodes: current.nodes.filter((node) => node.id !== nodeId),
      edges: current.edges.filter(
        (edge) => edge.source !== nodeId && edge.target !== nodeId,
      ),
    }));
    setSelectedNodeId(null);
    setPendingSourceId((current) => (current === nodeId ? null : current));
  };

  const completeConnection = (targetId: string) => {
    if (!pendingSourceId || pendingSourceId === targetId) return;
    changeWorkflow((current) => ({
      ...current,
      edges: [
        ...current.edges.filter(
          (edge) =>
            edge.source !== pendingSourceId && edge.target !== targetId,
        ),
        {
          id: uniqueId("edge"),
          source: pendingSourceId,
          target: targetId,
        },
      ],
    }));
    setPendingSourceId(null);
    setStatusMessage("Nodes connected. Save or run when you’re ready.");
  };

  const updateSelectedConfig = (
    key: keyof WorkflowNode["config"],
    value: string | number | boolean,
  ) => {
    if (!selectedNodeId) return;
    changeWorkflow((current) => ({
      ...current,
      nodes: current.nodes.map((node) =>
        node.id === selectedNodeId
          ? { ...node, config: { ...node.config, [key]: value } }
          : node,
      ),
    }));
  };

  const persistWorkflow = async (): Promise<Workflow> => {
    setSaving(true);
    try {
      const saved = await saveWorkflow({
        ...workflow,
        name: workflow.name.trim() || "Untitled workflow",
        status: "active",
      });
      setWorkflow(saved);
      setDirty(false);
      setWorkflows((current) => [
        saved,
        ...current.filter((item) => item.id !== saved.id),
      ]);
      setStatusMessage("Workflow saved.");
      return saved;
    } finally {
      setSaving(false);
    }
  };

  const handleSave = async () => {
    try {
      await persistWorkflow();
      onNotify("Workflow saved");
    } catch (error) {
      onNotify(error instanceof Error ? error.message : "Could not save workflow");
    }
  };

  const handleRun = async () => {
    setRunning(true);
    try {
      const saved = await persistWorkflow();
      const result = await runWorkflow(saved.id!);
      const updated = {
        ...saved,
        lastRunAt: result.createdAt,
        lastRunStatus: result.status,
      };
      setWorkflow(updated);
      setWorkflows((current) =>
        current.map((item) => (item.id === updated.id ? updated : item)),
      );
      setStatusMessage(
        result.status === "scheduled"
          ? "Automation scheduled successfully."
          : "Automation is running in the generation queue.",
      );
      onRunComplete(result);
    } catch (error) {
      const message =
        error instanceof Error ? error.message : "Could not run workflow";
      setStatusMessage(message);
      onNotify(message);
    } finally {
      setRunning(false);
    }
  };

  const loadWorkflow = (item: Workflow) => {
    setWorkflow(item);
    setSelectedNodeId(item.nodes[0]?.id ?? null);
    setPendingSourceId(null);
    setDirty(false);
    setStatusMessage("Workflow loaded. Edit nodes or run the automation.");
  };

  const createNewWorkflow = () => {
    const next = starterWorkflow();
    setWorkflow(next);
    setSelectedNodeId(next.nodes[0]?.id ?? null);
    setPendingSourceId(null);
    setDirty(true);
    setStatusMessage("New workflow ready to customize.");
  };

  return (
    <section className="workflow-page">
      <div className="workflow-page-heading">
        <div>
          <span className="page-kicker">
            <WorkflowIcon size={14} /> Automation builder
          </span>
          <h1>Workflows</h1>
          <p>
            Connect content, timing, and publishing nodes into repeatable video
            automations.
          </p>
        </div>
        <button
          className="primary-button"
          type="button"
          onClick={createNewWorkflow}
        >
          <CirclePlus size={17} /> New workflow
        </button>
      </div>

      <div className="workflow-builder">
        <aside className="workflow-palette">
          <div className="workflow-panel-title">
            <span>Node library</span>
            <small>Click to add</small>
          </div>
          <span className="palette-group-label">Content generators</span>
          <div className="palette-list">
            {projectModes.map((mode) => (
              <button
                className="palette-item"
                type="button"
                key={mode.id}
                disabled={!mode.available}
                onClick={() =>
                  addNode("content-generator", mode.id, mode.title)
                }
              >
                <span className={`palette-icon accent-${mode.accent}`}>
                  <mode.Icon size={16} />
                </span>
                <span>
                  <strong>{mode.title}</strong>
                  <small>{mode.available ? mode.engine : "Coming soon"}</small>
                </span>
                <CirclePlus size={14} />
              </button>
            ))}
          </div>

          <span className="palette-group-label">Flow controls</span>
          <button
            className="palette-item"
            type="button"
            onClick={() => addNode("scheduler", "delay", "Schedule")}
          >
            <span className="palette-icon palette-schedule">
              <CalendarClock size={16} />
            </span>
            <span>
              <strong>Scheduler</strong>
              <small>Delay or plan a run</small>
            </span>
            <CirclePlus size={14} />
          </button>

          <span className="palette-group-label">App connections</span>
          {destinationOptions.map((destination) => (
            <button
              className="palette-item"
              type="button"
              key={destination.id}
              disabled={!destination.available}
              onClick={() =>
                addNode(
                  "app-connection",
                  destination.id,
                  destination.label,
                )
              }
            >
              <span className={`palette-icon palette-${destination.id}`}>
                {destination.id === "youtube" ? (
                  <Youtube size={16} />
                ) : (
                  <Plug size={16} />
                )}
              </span>
              <span>
                <strong>{destination.label}</strong>
                <small>
                  {destination.available ? "Publishing app" : "Coming soon"}
                </small>
              </span>
              <CirclePlus size={14} />
            </button>
          ))}
        </aside>

        <div className="workflow-editor">
          <div className="workflow-toolbar">
            <div className="workflow-name-field">
              <WorkflowIcon size={16} />
              <input
                aria-label="Workflow name"
                value={workflow.name}
                onChange={(event) =>
                  changeWorkflow((current) => ({
                    ...current,
                    name: event.target.value,
                  }))
                }
              />
              {dirty ? <span title="Unsaved changes">Unsaved</span> : null}
            </div>
            <div className="workflow-toolbar-actions">
              <button
                type="button"
                disabled={saving || running}
                onClick={() => void handleSave()}
              >
                {saving ? (
                  <LoaderCircle className="spin" size={15} />
                ) : (
                  <Save size={15} />
                )}
                Save
              </button>
              <button
                className="run-workflow-button"
                type="button"
                disabled={saving || running}
                onClick={() => void handleRun()}
              >
                {running ? (
                  <LoaderCircle className="spin" size={15} />
                ) : (
                  <Play size={15} fill="currentColor" />
                )}
                {running ? "Starting…" : "Run automation"}
              </button>
            </div>
          </div>

          <div className="workflow-canvas-scroll">
            <div
              className={`workflow-canvas ${
                pendingSourceId ? "is-connecting" : ""
              }`}
              style={{ width: CANVAS_WIDTH, height: CANVAS_HEIGHT }}
              onClick={() => setSelectedNodeId(null)}
            >
              <div className="workflow-canvas-hint">
                {pendingSourceId
                  ? "Choose the input port on the next node"
                  : "Drag nodes · connect ports · configure · run"}
              </div>
              <svg
                className="workflow-edges"
                width={CANVAS_WIDTH}
                height={CANVAS_HEIGHT}
                aria-hidden="true"
              >
                {workflow.edges.map((edge) => {
                  const source = nodesById.get(edge.source);
                  const target = nodesById.get(edge.target);
                  if (!source || !target) return null;
                  const startX = source.x + NODE_WIDTH;
                  const startY = source.y + NODE_HEIGHT / 2;
                  const endX = target.x;
                  const endY = target.y + NODE_HEIGHT / 2;
                  const control = Math.max(70, Math.abs(endX - startX) * 0.5);
                  return (
                    <path
                      key={edge.id}
                      d={`M ${startX} ${startY} C ${startX + control} ${startY}, ${
                        endX - control
                      } ${endY}, ${endX} ${endY}`}
                    />
                  );
                })}
              </svg>
              {workflow.nodes.map((node) => {
                const mode = projectModes.find(
                  (item) => item.id === node.subtype,
                );
                const connection = connections.find(
                  (item) => item.provider === node.subtype,
                );
                const Icon =
                  mode?.Icon ??
                  (node.kind === "scheduler" ? CalendarClock : Plug);
                return (
                  <WorkflowNodeCard
                    key={node.id}
                    node={node}
                    Icon={Icon}
                    kicker={
                      node.kind === "content-generator"
                        ? "Content generator"
                        : node.kind === "scheduler"
                          ? "Flow control"
                          : connection?.status === "connected"
                            ? "App connected"
                            : "App connection"
                    }
                    detail={nodeDetail(node)}
                    tone={mode?.accent ?? node.kind.replace("-connection", "")}
                    selected={selectedNodeId === node.id}
                    connecting={pendingSourceId === node.id}
                    onSelect={setSelectedNodeId}
                    onMove={moveNode}
                    onStartConnection={setPendingSourceId}
                    onCompleteConnection={completeConnection}
                    onRemove={removeNode}
                  />
                );
              })}
            </div>
          </div>
          <div className="workflow-status-line" role="status">
            <span className="pipeline-dot" />
            {statusMessage}
          </div>
        </div>

        <aside className="workflow-inspector">
          <div className="workflow-panel-title">
            <span>Configuration</span>
            <small>{selectedNode ? "Selected node" : "No selection"}</small>
          </div>
          {selectedNode ? (
            <>
              <div className="inspector-node-heading">
                <span>
                  {selectedNode.kind === "content-generator" ? (
                    <Sparkles size={18} />
                  ) : selectedNode.kind === "scheduler" ? (
                    <Clock3 size={18} />
                  ) : (
                    <Plug size={18} />
                  )}
                </span>
                <div>
                  <strong>{selectedNode.label}</strong>
                  <small>{selectedNode.kind.replace("-", " ")}</small>
                </div>
              </div>
              {selectedNode.kind === "content-generator" ? (
                <div className="inspector-fields">
                  <label>
                    <span>Video idea</span>
                    <textarea
                      value={selectedNode.config.topic ?? ""}
                      placeholder="Leave blank to generate a lucky AI idea on every run."
                      rows={5}
                      maxLength={500}
                      onChange={(event) =>
                        updateSelectedConfig("topic", event.target.value)
                      }
                    />
                  </label>
                  <div className="inspector-grid">
                    <label>
                      <span>Duration</span>
                      <select
                        value={selectedNode.config.duration ?? 45}
                        onChange={(event) =>
                          updateSelectedConfig(
                            "duration",
                            Number(event.target.value),
                          )
                        }
                      >
                        {[30, 45, 60, 90].map((duration) => (
                          <option value={duration} key={duration}>
                            {duration} sec
                          </option>
                        ))}
                      </select>
                    </label>
                    <label>
                      <span>Language</span>
                      <select
                        value={selectedNode.config.language ?? "English"}
                        onChange={(event) =>
                          updateSelectedConfig("language", event.target.value)
                        }
                      >
                        {["English", "Turkish", "Spanish", "German", "French"].map(
                          (language) => (
                            <option key={language}>{language}</option>
                          ),
                        )}
                      </select>
                    </label>
                  </div>
                  <label>
                    <span>Niche</span>
                    <select
                      value={
                        selectedNode.config.niche ?? "general-storytelling"
                      }
                      onChange={(event) =>
                        updateSelectedConfig("niche", event.target.value)
                      }
                    >
                      <option value="general-storytelling">General story</option>
                      <option value="history">History</option>
                      <option value="horror">Horror</option>
                      <option value="psychology">Psychology</option>
                      <option value="motivation">Motivation</option>
                    </select>
                  </label>
                </div>
              ) : null}
              {selectedNode.kind === "scheduler" ? (
                <div className="inspector-fields">
                  <label>
                    <span>Run after</span>
                    <div className="number-field-suffix">
                      <input
                        type="number"
                        min={1}
                        max={10080}
                        value={selectedNode.config.delay_minutes ?? 5}
                        onChange={(event) =>
                          updateSelectedConfig(
                            "delay_minutes",
                            Number(event.target.value),
                          )
                        }
                      />
                      <span>minutes</span>
                    </div>
                  </label>
                  <div className="inspector-note">
                    The project is created now and dispatched automatically at
                    the scheduled time.
                  </div>
                </div>
              ) : null}
              {selectedNode.kind === "app-connection" ? (
                <div className="inspector-fields">
                  {(() => {
                    const connection = connections.find(
                      (item) => item.provider === selectedNode.subtype,
                    );
                    return (
                      <div
                        className={`inspector-connection ${
                          connection?.status === "connected"
                            ? "is-connected"
                            : ""
                        }`}
                      >
                        <span>
                          {connection?.status === "connected" ? (
                            <Check size={16} />
                          ) : (
                            <Plug size={16} />
                          )}
                        </span>
                        <div>
                          <strong>
                            {connection?.status === "connected"
                              ? "Ready to publish"
                              : "Connection required"}
                          </strong>
                          <small>
                            {connection?.accountLabel ??
                              `Connect ${selectedNode.label} before running.`}
                          </small>
                        </div>
                      </div>
                    );
                  })()}
                  <button
                    className="inspector-link-button"
                    type="button"
                    onClick={onNavigateConnections}
                  >
                    Manage app connections <ExternalLink size={14} />
                  </button>
                </div>
              ) : null}
            </>
          ) : (
            <div className="inspector-empty">
              <WorkflowIcon size={25} />
              <strong>Select a node</strong>
              <p>Configure its idea, timing, or publishing destination here.</p>
            </div>
          )}
        </aside>
      </div>

      <div className="workflow-table-card">
        <div className="workflow-table-heading">
          <div>
            <h2>Your workflows</h2>
            <p>Saved automations and their latest run.</p>
          </div>
          <span>{workflows.length} total</span>
        </div>
        <div className="workflow-table-scroll">
          <table>
            <thead>
              <tr>
                <th>Name</th>
                <th>Flow</th>
                <th>Status</th>
                <th>Last run</th>
                <th aria-label="Actions" />
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan={5} className="workflow-table-empty">
                    <LoaderCircle className="spin" size={18} /> Loading workflows
                  </td>
                </tr>
              ) : workflows.length ? (
                workflows.map((item) => (
                  <tr key={item.id}>
                    <td>
                      <strong>{item.name}</strong>
                      <small>{item.nodes.length} nodes</small>
                    </td>
                    <td>
                      <div className="workflow-mini-flow">
                        {item.nodes.map((node, index) => (
                          <span key={node.id}>
                            {node.kind === "content-generator" ? (
                              <Sparkles size={12} />
                            ) : node.kind === "scheduler" ? (
                              <CalendarClock size={12} />
                            ) : (
                              <Plug size={12} />
                            )}
                            {index < item.nodes.length - 1 ? (
                              <ChevronRight size={11} />
                            ) : null}
                          </span>
                        ))}
                      </div>
                    </td>
                    <td>
                      <span
                        className={`workflow-run-status status-${
                          item.lastRunStatus ?? item.status
                        }`}
                      >
                        {item.lastRunStatus ?? item.status}
                      </span>
                    </td>
                    <td>{formatLastRun(item.lastRunAt)}</td>
                    <td>
                      <button
                        type="button"
                        aria-label={`Edit ${item.name}`}
                        onClick={() => loadWorkflow(item)}
                      >
                        Edit <ChevronRight size={14} />
                      </button>
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={5} className="workflow-table-empty">
                    Save your first workflow to see it here.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </section>
  );
}
