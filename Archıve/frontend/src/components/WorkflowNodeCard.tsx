import {
  GripVertical,
  Link2,
  Trash2,
  type LucideIcon,
} from "lucide-react";
import { useRef, type PointerEvent } from "react";
import type { WorkflowNode } from "../types";

interface WorkflowNodeCardProps {
  node: WorkflowNode;
  Icon: LucideIcon;
  kicker: string;
  detail: string;
  tone: string;
  selected: boolean;
  connecting: boolean;
  onSelect: (nodeId: string) => void;
  onMove: (nodeId: string, deltaX: number, deltaY: number) => void;
  onStartConnection: (nodeId: string) => void;
  onCompleteConnection: (nodeId: string) => void;
  onRemove: (nodeId: string) => void;
}

export function WorkflowNodeCard({
  node,
  Icon,
  kicker,
  detail,
  tone,
  selected,
  connecting,
  onSelect,
  onMove,
  onStartConnection,
  onCompleteConnection,
  onRemove,
}: WorkflowNodeCardProps) {
  const previousPoint = useRef<{ x: number; y: number } | null>(null);
  const acceptsInput = node.kind !== "content-generator";
  const providesOutput = node.kind !== "app-connection";

  const handlePointerDown = (event: PointerEvent<HTMLDivElement>) => {
    const target = event.target as HTMLElement;
    if (target.closest("button")) return;
    event.currentTarget.setPointerCapture(event.pointerId);
    previousPoint.current = { x: event.clientX, y: event.clientY };
    onSelect(node.id);
  };

  const handlePointerMove = (event: PointerEvent<HTMLDivElement>) => {
    const previous = previousPoint.current;
    if (!previous || !event.currentTarget.hasPointerCapture(event.pointerId)) {
      return;
    }
    onMove(node.id, event.clientX - previous.x, event.clientY - previous.y);
    previousPoint.current = { x: event.clientX, y: event.clientY };
  };

  const handlePointerEnd = () => {
    previousPoint.current = null;
  };

  return (
    <article
      className={`workflow-node node-${tone} ${selected ? "is-selected" : ""}`}
      style={{ left: node.x, top: node.y }}
      onClick={(event) => {
        event.stopPropagation();
        onSelect(node.id);
      }}
    >
      {acceptsInput ? (
        <button
          className="node-port node-port-input"
          type="button"
          aria-label={`Connect into ${node.label}`}
          title="Connect into this node"
          onClick={(event) => {
            event.stopPropagation();
            onCompleteConnection(node.id);
          }}
        >
          <span />
        </button>
      ) : null}

      <div
        className="workflow-node-drag"
        onPointerDown={handlePointerDown}
        onPointerMove={handlePointerMove}
        onPointerUp={handlePointerEnd}
        onPointerCancel={handlePointerEnd}
      >
        <GripVertical size={14} />
        <span>{kicker}</span>
        <button
          type="button"
          aria-label={`Remove ${node.label}`}
          onClick={(event) => {
            event.stopPropagation();
            onRemove(node.id);
          }}
        >
          <Trash2 size={13} />
        </button>
      </div>
      <div className="workflow-node-body">
        <span className="workflow-node-icon">
          <Icon size={20} />
        </span>
        <div>
          <strong>{node.label}</strong>
          <small>{detail}</small>
        </div>
      </div>

      {providesOutput ? (
        <button
          className={`node-port node-port-output ${
            connecting ? "is-connecting" : ""
          }`}
          type="button"
          aria-label={`Connect from ${node.label}`}
          title="Start a connection"
          onClick={(event) => {
            event.stopPropagation();
            onStartConnection(node.id);
          }}
        >
          <Link2 size={11} />
        </button>
      ) : null}
    </article>
  );
}
