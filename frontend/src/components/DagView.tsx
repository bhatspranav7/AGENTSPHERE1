import { AGENT_COLORS, type NodeState, type RunState } from "../runState";

const W = 196;
const H = 62;
const COL = 250;
const ROW = 84;
const PAD = 16;

interface NodeBox {
  key: string;
  x: number;
  y: number;
  title: string;
  sub: string;
  color: string;
  state: NodeState;
  stepId?: number;
}

const STATE_GLYPH: Record<NodeState, { ch: string; color: string; label: string }> = {
  pending: { ch: "○", color: "var(--faint)", label: "Pending" },
  running: { ch: "◌", color: "var(--accent)", label: "Running" },
  retrying: { ch: "↻", color: "var(--warning)", label: "Retrying" },
  approved: { ch: "✓", color: "var(--good-text)", label: "Approved" },
  failed: { ch: "✕", color: "var(--critical-text)", label: "Aborted" },
  skipped: { ch: "–", color: "var(--faint)", label: "Skipped" },
};

function truncate(s: string, n: number) {
  return s.length > n ? s.slice(0, n - 1) + "…" : s;
}

export function DagView({
  run,
  selected,
  onSelect,
}: {
  run: RunState;
  selected: number | null;
  onSelect: (id: number) => void;
}) {
  const levels: number[][] = [];
  for (const id of run.order) {
    const lvl = run.steps[id].level ?? 0;
    (levels[lvl] ??= []).push(id);
  }
  const maxRows = Math.max(1, ...levels.map((l) => l?.length ?? 0));
  const height = PAD * 2 + maxRows * ROW - (ROW - H);
  const cols = levels.length + 2;
  const width = PAD * 2 + (cols - 1) * COL + W;
  const yFor = (i: number, n: number) => PAD + ((maxRows - n) * ROW) / 2 + i * ROW;

  const nodes: NodeBox[] = [];
  const pos: Record<string, NodeBox> = {};
  const add = (n: NodeBox) => {
    nodes.push(n);
    pos[n.key] = n;
  };

  add({
    key: "planner", x: PAD, y: yFor(0, 1), title: "Planner", color: AGENT_COLORS.planner, state: run.planner,
    sub: run.plans.length > 1 ? `strategist · plan v${run.plans.length}` : "strategist",
  });

  levels.forEach((ids, lvl) =>
    ids.forEach((id, i) => {
      const st = run.steps[id];
      add({
        key: `s${id}`, x: PAD + (lvl + 1) * COL, y: yFor(i, ids.length), stepId: id,
        title: truncate(st.title, 21), color: AGENT_COLORS[st.agent], state: st.state,
        sub: `${st.agent} · #${id}`,
      });
    }),
  );

  add({
    key: "reporter", x: PAD + (cols - 1) * COL, y: yFor(0, 1), title: "Reporter", color: AGENT_COLORS.reporter,
    state: run.reporter, sub: "narrator",
  });

  const edges: { from: NodeBox; to: NodeBox }[] = [];
  const hasChild = new Set<number>();
  for (const id of run.order) {
    const st = run.steps[id];
    if (!st.depends_on.length) edges.push({ from: pos.planner, to: pos[`s${id}`] });
    for (const d of st.depends_on) {
      hasChild.add(d);
      edges.push({ from: pos[`s${d}`], to: pos[`s${id}`] });
    }
  }
  for (const id of run.order) if (!hasChild.has(id)) edges.push({ from: pos[`s${id}`], to: pos.reporter });
  if (!run.order.length) edges.push({ from: pos.planner, to: pos.reporter });

  return (
    <div className="dag-wrap">
      <svg className="dag" style={{ width: "100%", maxWidth: width, minWidth: Math.min(width, 620) }} viewBox={`0 0 ${width} ${height}`} role="img"
           aria-label="Agent execution graph">
        {edges.map(({ from, to }, i) => {
          const x1 = from.x + W, y1 = from.y + H / 2, x2 = to.x, y2 = to.y + H / 2;
          const mx = (x1 + x2) / 2;
          const active = to.state === "running" || to.state === "retrying";
          const done = from.state === "approved" && (to.state === "approved" || active);
          return (
            <path key={i} className={`edge${active ? " active" : done ? " done" : ""}`}
                  d={`M${x1},${y1} C${mx},${y1} ${mx},${y2} ${x2},${y2}`} />
          );
        })}

        {nodes.map((n) => {
          const g = STATE_GLYPH[n.state];
          const verdicts = n.stepId ? run.steps[n.stepId].attempts.filter((a) => a.verdict).length : 0;
          const tries = n.stepId ? run.steps[n.stepId].attempts.length : 0;
          return (
            <g key={n.key}
               className={`node ${n.state}${n.stepId && n.stepId === selected ? " selected" : ""}`}
               transform={`translate(${n.x},${n.y})`}
               onClick={() => n.stepId && onSelect(n.stepId)}
               role={n.stepId ? "button" : undefined}
               tabIndex={n.stepId ? 0 : undefined}
               onKeyDown={(e) => n.stepId && (e.key === "Enter" || e.key === " ") && onSelect(n.stepId)}
               aria-label={`${n.title}: ${g.label}`}>
              <rect className="card" width={W} height={H} rx={11} />
              <rect x={0} y={10} width={3} height={H - 20} rx={1.5} fill={n.color} />
              <circle cx={28} cy={H / 2} r={13} fill={n.color} opacity={0.14} />
              <circle className="ring" cx={28} cy={H / 2} r={13} stroke={n.color}
                      strokeDasharray={n.state === "running" ? "20 62" : undefined}
                      opacity={n.state === "pending" ? 0.35 : 1} />
              <text x={28} y={H / 2 + 4.5} textAnchor="middle" fontSize={13} fontWeight={700} fill={n.color}>
                {n.title[0]}
              </text>
              <text className="title" x={50} y={27}>{n.title}</text>
              <text className="sub" x={50} y={45}>{n.sub}</text>
              <text x={W - 14} y={24} textAnchor="middle" fontSize={14} fontWeight={700} fill={g.color}>{g.ch}</text>
              {tries > 1 && (
                <text x={W - 14} y={H - 11} textAnchor="middle" fontSize={10} fontFamily="var(--mono)" fill="var(--warning)">
                  ×{tries}
                </text>
              )}
              {verdicts > 0 && (
                <g transform={`translate(${W - 42},${H - 24})`}>
                  <title>{verdicts} supervisor review{verdicts > 1 ? "s" : ""}</title>
                  <path d="M8 1 2 3.5v4C2 11 4.6 13.3 8 14c3.4-.7 6-3 6-6.5v-4L8 1Z" fill="none"
                        stroke={AGENT_COLORS.supervisor} strokeWidth={1.4} />
                  <text x={8} y={10.5} textAnchor="middle" fontSize={8} fontWeight={700} fill={AGENT_COLORS.supervisor}>
                    {verdicts}
                  </text>
                </g>
              )}
            </g>
          );
        })}
      </svg>
      <div className="dag-legend">
        {(["running", "retrying", "approved", "failed", "skipped"] as NodeState[]).map((s) => (
          <span key={s}>
            <b style={{ color: STATE_GLYPH[s].color }}>{STATE_GLYPH[s].ch}</b> {STATE_GLYPH[s].label}
          </span>
        ))}
        <span>
          <b style={{ color: AGENT_COLORS.supervisor }}>⛉</b> Supervisor reviews
        </span>
      </div>
    </div>
  );
}
