import type { Decision, RunStatus } from "../api";
import { IconAlert, IconCheck, IconRetry, IconSkip, IconStop, IconX } from "./icons";

const RUN: Record<RunStatus, { cls: string; label: string; live?: boolean }> = {
  queued: { cls: "", label: "Queued", live: true },
  planning: { cls: "info", label: "Planning", live: true },
  running: { cls: "info", label: "Running", live: true },
  completed: { cls: "ok", label: "Completed" },
  failed: { cls: "bad", label: "Failed" },
  aborted: { cls: "bad", label: "Aborted" },
  cancelled: { cls: "", label: "Cancelled" },
};

export function RunStatusPill({ status }: { status: RunStatus | string }) {
  const s = RUN[status as RunStatus] ?? { cls: "", label: status };
  return (
    <span className={`pill ${s.cls}${s.live ? " live" : ""}`}>
      <span className="dot" /> {s.label}
    </span>
  );
}

const DECISION = {
  APPROVE: { color: "var(--good-text)", Icon: IconCheck, label: "Approve" },
  RETRY: { color: "var(--warning)", Icon: IconRetry, label: "Retry" },
  ABORT: { color: "var(--critical-text)", Icon: IconX, label: "Abort" },
};

export function DecisionTag({ decision }: { decision: Decision }) {
  const d = DECISION[decision];
  return (
    <span className="status-icon" style={{ color: d.color }}>
      <d.Icon /> {d.label.toUpperCase()}
    </span>
  );
}

export function ActionStatus({ status }: { status: string }) {
  const map: Record<string, { color: string; Icon: typeof IconCheck }> = {
    success: { color: "var(--good-text)", Icon: IconCheck },
    skipped: { color: "var(--muted)", Icon: IconSkip },
    failed: { color: "var(--critical-text)", Icon: IconAlert },
  };
  const s = map[status] ?? { color: "var(--muted)", Icon: IconStop };
  return (
    <span className="status-icon" style={{ color: s.color }}>
      <s.Icon /> {status}
    </span>
  );
}

export function ScoreBar({ score }: { score: number }) {
  const color = score >= 0.6 ? "var(--good)" : score >= 0.3 ? "var(--warning)" : "var(--critical)";
  return (
    <span style={{ display: "inline-flex", alignItems: "center", gap: 8 }}>
      <span className="score-bar">
        <span style={{ width: `${Math.max(score, 0.02) * 100}%`, background: color }} />
      </span>
      <span className="num">{score.toFixed(2)}</span>
    </span>
  );
}
