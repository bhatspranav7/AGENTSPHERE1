import { useEffect, useMemo, useState, type ReactNode } from "react";
import type { ExecEvent } from "../api";
import { clock, duration } from "../format";
import { AGENT_COLORS, type Attempt, type PlanVersion, type RunState, type StepState, type Verdict } from "../runState";
import { IconAlert, IconBolt, IconCheck, IconCopy, IconDoc, IconGraph, IconRetry, IconShield, IconSkip, IconX } from "./icons";
import { ActionStatus, DecisionTag, ScoreBar } from "./Status";

// -------------------------------------------------
// EVENT FEED
// -------------------------------------------------
function describe(e: ExecEvent, run: RunState): { icon: ReactNode; color: string; text: ReactNode } | null {
  const p = e.payload;
  const step = p.step_id ? run.steps[p.step_id] : undefined;
  const who = step ? <b style={{ color: AGENT_COLORS[step.agent] }}>{step.title}</b> : null;

  switch (e.type) {
    case "execution.queued":
      return { icon: <IconBolt />, color: "var(--muted)", text: "Execution queued" };
    case "execution.started":
      return { icon: <IconBolt />, color: "var(--accent)", text: <>Started with <b>{p.llm_mode}</b> LLM{p.chaos !== "off" && <> · chaos <b>{p.chaos}</b></>}</> };
    case "agent.started":
      return { icon: <IconGraph />, color: AGENT_COLORS[p.agent as "planner"], text: p.agent === "planner" ? `Planner drafting plan (attempt ${p.attempt})` : "Reporter writing the summary" };
    case "plan.proposed":
      return { icon: <IconDoc />, color: "var(--accent)", text: <>Plan v{p.version} proposed · {p.plan?.steps?.length ?? 0} steps{p.injected_fault && <span style={{ color: "var(--warning)" }}> · fault injected</span>}</> };
    case "graph.ready":
      return { icon: <IconGraph />, color: "var(--accent)", text: <>Task graph ready · {p.nodes.length} steps, depth {p.depth}{p.fallback && " (fallback)"}</> };
    case "step.started":
      return { icon: <IconBolt />, color: step ? AGENT_COLORS[step.agent] : "var(--muted)", text: <>{who} started{p.attempt > 1 && ` (attempt ${p.attempt})`}</> };
    case "step.output":
      return { icon: <IconDoc />, color: "var(--muted)", text: <>{who} produced output in {duration(p.latency_ms)}{p.injected_fault && <span style={{ color: "var(--warning)" }}> · {p.injected_fault} fault</span>}</> };
    case "supervisor.decision": {
      const icon = p.decision === "APPROVE" ? <IconCheck /> : p.decision === "RETRY" ? <IconRetry /> : <IconX />;
      const color = p.decision === "APPROVE" ? "var(--good-text)" : p.decision === "RETRY" ? "var(--warning)" : "var(--critical-text)";
      return { icon, color, text: <>Supervisor <b style={{ color }}>{p.decision}</b> {p.target === "plan" ? `plan v${p.attempt}` : who} · {p.score.toFixed(2)}{p.decision !== "APPROVE" && <div className="faint" style={{ fontSize: 12 }}>{p.reason}</div>}</> };
    }
    case "step.completed":
      return null;
    case "step.failed":
      return { icon: <IconX />, color: "var(--critical-text)", text: <>{who} aborted</> };
    case "step.skipped":
      return { icon: <IconSkip />, color: "var(--faint)", text: <>{who} skipped</> };
    case "report.ready":
      return { icon: <IconDoc />, color: AGENT_COLORS.reporter, text: "Final report ready" };
    case "execution.completed":
      return { icon: <IconCheck />, color: "var(--good-text)", text: <b>Execution completed in {duration(p.duration_ms)}</b> };
    case "execution.aborted":
      return { icon: <IconShield />, color: "var(--critical-text)", text: <><b>Aborted by Supervisor</b><div className="faint" style={{ fontSize: 12 }}>{p.reason}</div></> };
    case "execution.failed":
      return { icon: <IconAlert />, color: "var(--critical-text)", text: <><b>Execution failed</b><div className="faint" style={{ fontSize: 12 }}>{p.reason}</div></> };
    case "execution.cancelled":
      return { icon: <IconX />, color: "var(--muted)", text: <b>Cancelled</b> };
    default:
      return null;
  }
}

export function EventFeed({ run, connection }: { run: RunState; connection: string }) {
  const items = run.events.map((e) => ({ e, d: describe(e, run) })).filter((x) => x.d).reverse();
  return (
    <div className="panel">
      <div className="panel-head">
        <div className="label">Live event stream</div>
        <span className={`pill ${connection === "live" ? "ok live" : connection === "connecting" ? "warn" : ""}`}>
          <span className="dot" /> {connection === "live" ? "SSE live" : connection}
        </span>
      </div>
      <div className="feed" aria-live="polite">
        {items.length === 0 && <div className="muted" style={{ fontSize: 14 }}>Waiting for the first event…</div>}
        {items.map(({ e, d }) => (
          <div key={e.id} className="feed-item">
            <span className="feed-dot" style={{ color: d!.color }}>{d!.icon}</span>
            <div className="feed-text">
              {d!.text}
              <time>{clock(e.ts)} · #{e.id}</time>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// -------------------------------------------------
// VERDICT
// -------------------------------------------------
export function VerdictCard({ v, title }: { v: Verdict; title?: ReactNode }) {
  return (
    <div className={`verdict ${v.decision}`}>
      <div className="verdict-top">
        <DecisionTag decision={v.decision} />
        {title && <span style={{ fontSize: 14, fontWeight: 600 }}>{title}</span>}
        <span className="faint mono" style={{ fontSize: 11 }}>attempt {v.attempt}</span>
        <span style={{ marginLeft: "auto" }}><ScoreBar score={v.score} /></span>
      </div>
      <p>{v.reason}</p>
      {v.feedback && v.decision !== "APPROVE" && (
        <p style={{ color: "var(--text)" }}><span className="label">Feedback → agent</span><br />{v.feedback}</p>
      )}
      {v.injected_fault && (
        <p style={{ color: "var(--warning)" }}>Chaos: a <b>{v.injected_fault}</b> fault was injected into this output on purpose.</p>
      )}
      <div className="checks">
        {v.checks.map((c) => (
          <span key={c.name} className={`check ${c.passed ? "pass" : "fail"}`} title={c.detail !== undefined ? JSON.stringify(c.detail) : undefined}>
            {c.passed ? "✓" : "✕"} {c.name.replace(/_/g, " ")}
            {typeof c.detail === "number" || typeof c.detail === "string" ? <span className="faint"> {String(c.detail).slice(0, 24)}</span> : null}
          </span>
        ))}
      </div>
    </div>
  );
}

// -------------------------------------------------
// CODE VIEWER (tiny tokenizer, no dependency)
// -------------------------------------------------
const TOKEN = /(#.*$|"""[\s\S]*?"""|"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*'|\b(?:def|class|return|import|from|if|else|elif|for|in|not|raise|with|as|async|await|None|True|False|const|let|function|export|try|except|lambda|and|or|is)\b|\b\d+(?:\.\d+)?\b|@\w+)/gm;

function highlight(code: string): ReactNode[] {
  return code.split("\n").map((line, i) => {
    const parts: ReactNode[] = [];
    let last = 0;
    for (const m of line.matchAll(TOKEN)) {
      const t = m[0];
      if (m.index! > last) parts.push(line.slice(last, m.index));
      const cls = t.startsWith("#") ? "tok-c" : /^["']/.test(t) ? "tok-s" : /^\d/.test(t) ? "tok-n" : t.startsWith("@") ? "tok-d" : "tok-k";
      parts.push(<span key={m.index} className={cls}>{t}</span>);
      last = m.index! + t.length;
    }
    parts.push(line.slice(last));
    return <span key={i} className="l">{parts}{"\n"}</span>;
  });
}

function CodeFiles({ files }: { files: { path: string; content: string }[] }) {
  const [active, setActive] = useState(0);
  const [copied, setCopied] = useState(false);
  const file = files[Math.min(active, files.length - 1)];
  const lines = useMemo(() => highlight(file.content), [file.content]);

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(file.content);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1200);
    } catch {
      /* clipboard blocked */
    }
  };

  return (
    <div className="code-block">
      <div className="code-tabs">
        {files.map((f, i) => (
          <button key={f.path} className={i === active ? "on" : ""} onClick={() => setActive(i)}>{f.path}</button>
        ))}
        <span className="spacer" />
        <button onClick={copy} aria-label="Copy file"><IconCopy width={13} height={13} /> {copied ? "Copied" : "Copy"}</button>
      </div>
      <pre className="code">{lines}</pre>
    </div>
  );
}

// -------------------------------------------------
// AGENT OUTPUT
// -------------------------------------------------
function Output({ agent, output }: { agent: string; output: Record<string, any> }) {
  const list = (items: unknown, cls = "") =>
    Array.isArray(items) && items.length ? (
      <ul className={`list ${cls}`}>{items.map((x, i) => <li key={i}><span>{String(x)}</span></li>)}</ul>
    ) : <p className="faint" style={{ margin: 0 }}>—</p>;

  return (
    <div>
      <p style={{ margin: 0, lineHeight: 1.6, fontSize: 15 }}>{String(output.summary ?? "(no summary)")}</p>

      {agent === "research" && (
        <>
          <div className="label section-label">Findings</div>
          {list(output.findings)}
          {output.risks?.length > 0 && (<><div className="label section-label">Risks</div>{list(output.risks, "risk")}</>)}
          <div className="label section-label">Recommendations</div>
          {list(output.recommendations)}
        </>
      )}

      {agent === "code" && (
        <>
          <div className="label section-label">Files · {output.language}</div>
          {Array.isArray(output.files) && output.files.length ? <CodeFiles files={output.files} /> : <p className="faint">No files</p>}
          {output.how_to_run && (
            <>
              <div className="label section-label">Run it</div>
              <pre className="json">{output.how_to_run}</pre>
            </>
          )}
        </>
      )}

      {agent === "automation" && (
        <>
          <div className="label section-label">Actions</div>
          {Array.isArray(output.actions) ? (
            <div style={{ overflowX: "auto" }}>
              <table className="action-table">
                <tbody>
                  {output.actions.map((a: any, i: number) => (
                    <tr key={i}>
                      <td><ActionStatus status={a.status} /></td>
                      <td><b>{a.name}</b><div className="muted" style={{ marginTop: 3 }}>{a.detail}</div></td>
                      <td className="mono faint" style={{ fontSize: 12, whiteSpace: "nowrap" }}>{a.system}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : <p className="faint">No actions</p>}
          {output.outcome && (<><div className="label section-label">Outcome</div><p style={{ margin: 0 }}>{output.outcome}</p></>)}
        </>
      )}
    </div>
  );
}

export function StepDetail({ step }: { step: StepState }) {
  const [attemptNo, setAttemptNo] = useState<number | null>(null);
  const last = step.attempts[step.attempts.length - 1];
  const current: Attempt | undefined = step.attempts.find((a) => a.attempt === attemptNo) ?? last;

  useEffect(() => setAttemptNo(null), [step.step_id]);

  return (
    <div>
      <div className="step-head">
        <span className="agent-badge" style={{ color: AGENT_COLORS[step.agent] }}>{step.agent}</span>
        <h3 style={{ margin: 0, fontSize: 19 }}>{step.title}</h3>
        {step.depends_on.length > 0 && <span className="faint mono" style={{ fontSize: 11.5 }}>after #{step.depends_on.join(", #")}</span>}
      </div>
      <p className="muted" style={{ marginTop: 0, lineHeight: 1.55 }}>{step.objective}</p>

      {step.attempts.length > 1 && (
        <div className="attempts">
          {step.attempts.map((a) => (
            <button key={a.attempt} className={`attempt-tab${a === current ? " on" : ""}`} onClick={() => setAttemptNo(a.attempt)}>
              {a.verdict?.decision === "APPROVE" ? <IconCheck width={12} height={12} color="var(--good-text)" />
                : a.verdict?.decision === "RETRY" ? <IconRetry width={12} height={12} color="var(--warning)" />
                : a.verdict?.decision === "ABORT" ? <IconX width={12} height={12} color="var(--critical-text)" /> : null}
              attempt {a.attempt}
            </button>
          ))}
        </div>
      )}

      {!current?.output ? (
        <div className="muted" style={{ padding: "20px 0" }}>
          {step.state === "running" ? "Agent is working…" : step.state === "skipped" ? "This step never ran." : "Waiting for dependencies…"}
        </div>
      ) : (
        <>
          <div className="meta" style={{ marginBottom: 14 }}>
            <span className="pill">{duration(current.latency_ms)}</span>
            <span className="pill">{current.tokens ?? 0} tokens</span>
            {current.injected_fault && <span className="pill warn"><span className="dot" /> injected: {current.injected_fault}</span>}
            {current.llm_error && <span className="pill bad"><span className="dot" /> {current.llm_error}</span>}
          </div>
          {current.verdict && <div style={{ marginBottom: 18 }}><VerdictCard v={current.verdict} title="Supervisor review" /></div>}
          <Output agent={step.agent} output={current.output} />
        </>
      )}
    </div>
  );
}

// -------------------------------------------------
// PLANS / REPORT / SUPERVISOR LOG
// -------------------------------------------------
export function PlanVersions({ plans }: { plans: PlanVersion[] }) {
  const [open, setOpen] = useState<number | null>(null);
  if (!plans.length) return <div className="muted">The planner hasn't proposed a plan yet.</div>;
  return (
    <div className="stack">
      {plans.map((p) => (
        <div key={p.version}>
          {p.verdict ? <VerdictCard v={p.verdict} title={<>Plan v{p.version} <span className="faint mono" style={{ fontSize: 11 }}>{p.source}</span></>} />
            : <div className="verdict"><b>Plan v{p.version}</b> <span className="muted">under review…</span></div>}
          <button className="btn sm ghost" style={{ marginTop: 8 }} onClick={() => setOpen(open === p.version ? null : p.version)}>
            {open === p.version ? "Hide" : "Show"} plan JSON
          </button>
          {open === p.version && <pre className="json" style={{ marginTop: 8 }}>{JSON.stringify(p.plan, null, 2)}</pre>}
        </div>
      ))}
    </div>
  );
}

export function SupervisorLog({ run }: { run: RunState }) {
  if (!run.verdicts.length) return <div className="muted">No decisions yet.</div>;
  return (
    <div className="stack" style={{ gap: 10 }}>
      {[...run.verdicts].reverse().map((v, i) => (
        <VerdictCard key={i} v={v} title={v.target === "plan" ? `Plan v${v.attempt}` : run.steps[v.step_id!]?.title ?? `Step ${v.step_id}`} />
      ))}
    </div>
  );
}

export function ReportView({ report }: { report: Record<string, any> }) {
  return (
    <div className="panel report">
      <div className="label" style={{ color: "var(--good-text)" }}>Final report</div>
      <h2>{report.title}</h2>
      <p>{report.executive_summary}</p>
      <div className="two-col" style={{ marginTop: 18 }}>
        <div>
          <div className="label section-label">Key outcomes</div>
          <ul className="list">{(report.key_outcomes ?? []).map((x: string, i: number) => <li key={i}><span>{x}</span></li>)}</ul>
        </div>
        <div>
          <div className="label section-label">Next steps</div>
          <ul className="list">{(report.next_steps ?? []).map((x: string, i: number) => <li key={i}><span>{x}</span></li>)}</ul>
        </div>
      </div>
      {Array.isArray(report.memory) && report.memory.length > 0 && (
        <p className="faint mono" style={{ fontSize: 11.5, marginTop: 16 }}>
          Redis workflow memory: {report.memory.length} entries ·{" "}
          {report.memory.map((m: any) => `#${m.step_id}×${m.attempts}`).join(" ")}
        </p>
      )}
    </div>
  );
}
