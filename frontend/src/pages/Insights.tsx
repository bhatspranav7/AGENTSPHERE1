import { useEffect, useRef, useState } from "react";
import { api, type AgentStat, type Metrics } from "../api";
import { useApp } from "../app-context";
import { IconCheck, IconRetry, IconX } from "../components/icons";
import { compact, duration, pct } from "../format";
import { AGENT_COLORS } from "../runState";

// Categorical slots validated for the dark surface (blue / orange)
const SERIES = [
  { key: "completed", label: "Completed", color: "var(--series-1)" },
  { key: "unsuccessful", label: "Aborted, failed or cancelled", color: "var(--series-2)" },
];

function niceMax(n: number) {
  if (n <= 4) return 4;
  const pow = 10 ** Math.floor(Math.log10(n));
  const step = [1, 2, 2.5, 5, 10].map((m) => m * pow).find((s) => n / s <= 4) ?? pow * 10;
  return Math.ceil(n / step) * step;
}

function useWidth<T extends HTMLElement>(fallback: number) {
  const ref = useRef<T>(null);
  const [width, setWidth] = useState(fallback);
  useEffect(() => {
    if (!ref.current) return;
    const ro = new ResizeObserver(([entry]) => setWidth(Math.max(260, Math.round(entry.contentRect.width))));
    ro.observe(ref.current);
    return () => ro.disconnect();
  }, []);
  return [ref, width] as const;
}

function DailyRuns({ daily }: { daily: Metrics["daily"] }) {
  const [hover, setHover] = useState<number | null>(null);
  const [ref, W] = useWidth<HTMLDivElement>(640);
  const rows = daily.map((d) => {
    const completed = Number(d.completed ?? 0);
    const unsuccessful = Number(d.aborted ?? 0) + Number(d.failed ?? 0) + Number(d.cancelled ?? 0);
    return { date: d.date as string, completed, unsuccessful, total: completed + unsuccessful };
  });
  const max = niceMax(Math.max(1, ...rows.map((r) => r.total)));
  const H = 220, L = 34, B = 24, T = 8;
  const plotW = W - L, plotH = H - B - T;
  const band = plotW / rows.length;
  const barW = Math.min(26, band * 0.62);
  const y = (v: number) => T + plotH - (v / max) * plotH;
  const ticks = [0, max / 2, max];

  return (
    <div className="chart" ref={ref} onMouseLeave={() => setHover(null)}>
      <svg width={W} height={H} viewBox={`0 0 ${W} ${H}`} role="img" aria-label="Executions per day, completed versus unsuccessful">
        {ticks.map((t) => (
          <g key={t}>
            <line className={t === 0 ? "baseline" : "gridline"} x1={L} x2={W} y1={y(t)} y2={y(t)} />
            <text className="tick" x={L - 8} y={y(t) + 3} textAnchor="end">{t}</text>
          </g>
        ))}
        {rows.map((r, i) => {
          const x = L + i * band + (band - barW) / 2;
          const hC = (r.completed / max) * plotH;
          const hU = (r.unsuccessful / max) * plotH;
          const gap = r.completed && r.unsuccessful ? 2 : 0;
          const d = new Date(r.date + "T00:00:00");
          return (
            <g key={r.date} className={`col${hover === i ? " hover" : ""}`}>
              {r.completed > 0 && <rect x={x} y={y(r.completed)} width={barW} height={hC} rx={Math.min(4, hC / 2)} fill="var(--series-1)" />}
              {r.unsuccessful > 0 && (
                <rect x={x} y={y(r.total)} width={barW} height={Math.max(hU - gap, 1)} rx={Math.min(4, hU / 2)} fill="var(--series-2)" />
              )}
              {i % Math.ceil(rows.length / Math.max(2, Math.floor(W / 64))) === 0 && (
                <text className="tick" x={x + barW / 2} y={H - 6} textAnchor="middle">
                  {d.toLocaleDateString(undefined, { day: "numeric", month: "short" })}
                </text>
              )}
              <rect className="hit" x={L + i * band} y={T} width={band} height={plotH} onMouseEnter={() => setHover(i)}
                    onFocus={() => setHover(i)} tabIndex={0} aria-label={`${r.date}: ${r.completed} completed, ${r.unsuccessful} unsuccessful`} />
            </g>
          );
        })}
      </svg>
      {hover !== null && (
        <div className="tooltip" style={{ left: `${((L + hover * band + band / 2) / W) * 100}%`, top: `${(y(rows[hover].total) / H) * 100}%` }}>
          <b>{new Date(rows[hover].date + "T00:00:00").toLocaleDateString(undefined, { weekday: "short", day: "numeric", month: "short" })}</b>
          {SERIES.map((s) => (
            <div key={s.key} className="row">
              <span><span className="swatch" style={{ background: s.color }} />{s.label.split(",")[0]}</span>
              <b>{rows[hover][s.key as "completed" | "unsuccessful"]}</b>
            </div>
          ))}
        </div>
      )}
      <div className="legend" style={{ marginTop: 10 }}>
        {SERIES.map((s) => <span key={s.key}><span className="swatch" style={{ background: s.color }} />{s.label}</span>)}
      </div>
    </div>
  );
}

const DECISIONS = [
  { key: "APPROVE", label: "Approved", color: "var(--good)", Icon: IconCheck, text: "var(--good-text)" },
  { key: "RETRY", label: "Sent back for retry", color: "var(--warning)", Icon: IconRetry, text: "var(--warning)" },
  { key: "ABORT", label: "Aborted", color: "var(--critical)", Icon: IconX, text: "var(--critical-text)" },
];

export default function Insights() {
  const { apiKey } = useApp();
  const [m, setM] = useState<Metrics | null>(null);
  const [agents, setAgents] = useState<AgentStat[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!apiKey) return;
    const load = () => {
      api.metrics().then(setM).catch((e) => setError(e.message));
      api.agents().then(setAgents).catch(() => {});
    };
    load();
    const t = window.setInterval(load, 10000);
    return () => window.clearInterval(t);
  }, [apiKey]);

  const decisionTotal = m ? DECISIONS.reduce((n, d) => n + (m.supervisor_decisions[d.key] ?? 0), 0) : 0;
  const workers = agents?.filter((a) => a.attempts > 0) ?? [];
  const maxLatency = Math.max(1, ...workers.map((a) => a.avg_latency_ms ?? 0));

  return (
    <>
      <div className="page-head">
        <div>
          <div className="label">Observability</div>
          <h1>Insights</h1>
          <p>How the crew is performing: throughput, reliability, and how often the Supervisor had to step in.</p>
        </div>
      </div>
      {error && <p className="error">{error}</p>}

      {!m ? (
        <div className="skeleton" style={{ minHeight: 300 }} />
      ) : (
        <>
          <div className="tiles">
            <div className="panel tile hero">
              <div className="label">Success rate</div>
              <div className="value">{pct(m.success_rate)}</div>
              <div className="hint">{m.by_status.completed ?? 0} of {m.total_executions} executions completed</div>
            </div>
            <div className="panel tile">
              <div className="label">Avg duration</div>
              <div className="value">{duration(m.avg_duration_ms)}</div>
              <div className="hint">p95 {duration(m.p95_duration_ms)}</div>
            </div>
            <div className="panel tile">
              <div className="label">Supervisor retries</div>
              <div className="value">{compact(m.supervisor_decisions.RETRY ?? 0)}</div>
              <div className="hint">faults caught before they spread</div>
            </div>
            <div className="panel tile">
              <div className="label">Tokens</div>
              <div className="value">{compact(m.total_tokens)}</div>
              <div className="hint">across completed runs</div>
            </div>
          </div>

          <div className="chart-grid">
            <div className="panel">
              <div className="panel-head"><div className="label">Executions per day · last 14 days</div></div>
              <DailyRuns daily={m.daily} />
            </div>

            <div className="panel">
              <div className="panel-head"><div className="label">Supervisor verdicts</div><span className="num">{decisionTotal} total</span></div>
              <div className="proportion" role="img" aria-label="Share of supervisor decisions">
                {DECISIONS.map((d) => {
                  const n = m.supervisor_decisions[d.key] ?? 0;
                  return n ? <span key={d.key} style={{ flex: n, background: d.color }} title={`${d.label}: ${n}`} /> : null;
                })}
              </div>
              <div className="decision-rows">
                {DECISIONS.map((d) => {
                  const n = m.supervisor_decisions[d.key] ?? 0;
                  return (
                    <div key={d.key} className="decision-row">
                      <span className="status-icon" style={{ color: d.text, fontSize: 13 }}><d.Icon /> {d.label}</span>
                      <span className="num">{decisionTotal ? pct(n / decisionTotal) : "—"}</span>
                      <b className="num" style={{ color: "var(--text)" }}>{n}</b>
                    </div>
                  );
                })}
              </div>
              <p className="faint" style={{ fontSize: 12.5, lineHeight: 1.5, marginBottom: 0 }}>
                Every plan and every agent output is reviewed. Retries carry the Supervisor's feedback back to the agent.
              </p>
            </div>
          </div>

          <div className="panel">
            <div className="panel-head"><div className="label">Agent performance</div></div>
            {workers.length === 0 ? (
              <div className="empty">No agent activity yet.</div>
            ) : (
              <div style={{ overflowX: "auto" }}>
                <table className="agent-table">
                  <thead>
                    <tr><th>Agent</th><th>Attempts</th><th>First-pass approval</th><th>Avg latency</th><th>Tokens</th></tr>
                  </thead>
                  <tbody>
                    {workers.map((a) => (
                      <tr key={a.name}>
                        <td>
                          <span className="agent-badge" style={{ color: AGENT_COLORS[a.name as "code"] ?? a.color }}>{a.name}</span>
                          <span className="muted" style={{ marginLeft: 10, fontSize: 13 }}>{a.role}</span>
                        </td>
                        <td className="num">{a.attempts}</td>
                        <td className="num">{pct(a.approval_rate)}</td>
                        <td>
                          <div className="inline-bar">
                            <span className="track"><span style={{ width: `${((a.avg_latency_ms ?? 0) / maxLatency) * 100}%` }} /></span>
                            <span className="num">{duration(a.avg_latency_ms)}</span>
                          </div>
                        </td>
                        <td className="num">{compact(a.tokens)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </>
      )}
    </>
  );
}
