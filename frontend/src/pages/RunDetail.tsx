import { useEffect, useMemo, useReducer, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api, streamEvents, TERMINAL, type Run, type RunStatus } from "../api";
import { useApp } from "../app-context";
import { DagView } from "../components/DagView";
import { IconAlert, IconRetry, IconShield, IconStop } from "../components/icons";
import { EventFeed, PlanVersions, ReportView, StepDetail, SupervisorLog } from "../components/RunParts";
import { RunStatusPill } from "../components/Status";
import { compact, duration, shortId } from "../format";
import { initialRun, reduce, type RunState } from "../runState";

type Tab = "step" | "supervisor" | "plans";

export default function RunDetail() {
  const { id = "" } = useParams();
  const navigate = useNavigate();
  const { toast, apiKey } = useApp();

  const [summary, setSummary] = useState<Run | null>(null);
  const [notFound, setNotFound] = useState(false);
  const [run, dispatch] = useReducer(reduce, initialRun);
  const [connection, setConnection] = useState("connecting");
  const [selected, setSelected] = useState<number | null>(null);
  const [tab, setTab] = useState<Tab>("step");
  const [now, setNow] = useState(Date.now());

  useEffect(() => {
    if (!apiKey) return;
    api.run(id).then(setSummary).catch(() => setNotFound(true));
    return streamEvents(id, dispatch, setConnection);
  }, [id, apiKey]);

  const status = (run.events.length ? run.status : summary?.status ?? "queued") as RunStatus;
  const terminal = TERMINAL.includes(status);

  // Refresh persisted totals once the run ends
  useEffect(() => {
    if (terminal) api.run(id).then(setSummary).catch(() => {});
  }, [terminal, id]);

  useEffect(() => {
    if (terminal) return;
    const t = window.setInterval(() => setNow(Date.now()), 200);
    return () => window.clearInterval(t);
  }, [terminal]);

  // Follow the action: select whichever step is currently working
  const activeStep = useMemo(
    () => run.order.find((sid) => ["running", "retrying"].includes(run.steps[sid].state)),
    [run],
  );
  useEffect(() => {
    if (activeStep !== undefined && tab === "step") setSelected(activeStep);
  }, [activeStep, tab]);

  const elapsed = run.stats?.duration_ms ?? summary?.duration_ms ??
    (run.startedAt ? now - new Date(run.startedAt).getTime() : null);

  const cancel = async () => {
    try {
      await api.cancel(id);
      toast("Cancelling execution…");
    } catch (e) {
      toast(e instanceof Error ? e.message : "Cancel failed", "err");
    }
  };

  const replay = async () => {
    try {
      const r = await api.replay(id);
      navigate(`/runs/${r.execution_id}`);
    } catch (e) {
      toast(e instanceof Error ? e.message : "Replay failed", "err");
    }
  };

  if (notFound) {
    return (
      <div className="panel empty" style={{ marginTop: 30 }}>
        <p>Execution not found.</p>
        <Link to="/runs" className="btn">← All runs</Link>
      </div>
    );
  }

  const step = selected !== null ? run.steps[selected] : run.steps[run.order[0]];
  const retries = run.verdicts.filter((v) => v.decision === "RETRY").length;
  const tokens = run.stats?.total_tokens ?? summary?.total_tokens ?? 0;
  const approved = Object.values(run.steps).filter((s) => s.state === "approved").length;

  return (
    <>
      <div className="run-head">
        <div>
          <Link to="/runs" className="label" style={{ color: "var(--accent)" }}>← Runs / {shortId(id)}</Link>
          <h1>{run.objective ?? summary?.objective ?? "Loading…"}</h1>
          <div className="meta">
            <RunStatusPill status={status} />
            {(run.llmMode ?? summary?.llm_mode) && (
              <span className={`pill ${(run.llmMode ?? summary?.llm_mode) === "live" ? "violet" : "info"}`}>
                <span className="dot" /> {(run.llmMode ?? summary?.llm_mode) === "live" ? run.llmModel ?? summary?.llm_model : "simulated LLM"}
              </span>
            )}
            {(run.chaos ?? summary?.chaos) && (run.chaos ?? summary?.chaos) !== "off" && (
              <span className="pill warn"><span className="dot" /> chaos: {run.chaos ?? summary?.chaos}</span>
            )}
            {summary?.parent_id && (
              <Link to={`/runs/${summary.parent_id}`} className="pill"><IconRetry width={12} height={12} /> replay of {shortId(summary.parent_id)}</Link>
            )}
          </div>
        </div>
        <div style={{ display: "flex", gap: 8 }}>
          {!terminal && <button className="btn danger" onClick={cancel}><IconStop /> Cancel</button>}
          {terminal && <button className="btn" onClick={replay}><IconRetry /> Replay</button>}
        </div>
      </div>

      {(status === "aborted" || status === "failed") && (
        <div className="banner">
          {status === "aborted" ? <IconShield color="var(--critical-text)" /> : <IconAlert color="var(--critical-text)" />}
          <div>
            <b>{status === "aborted" ? "The Supervisor aborted this workflow." : "This execution failed."}</b>
            <div className="muted">{run.reason ?? summary?.error}</div>
          </div>
        </div>
      )}
      {run.fallback && (
        <div className="banner warn">
          <IconAlert color="var(--warning)" />
          <div>The planner couldn't produce an approvable plan, so the deterministic fallback plan was used.</div>
        </div>
      )}

      <div className="kpis">
        <div className="kpi">
          <div className="label">Elapsed</div>
          <div className="value">{duration(elapsed == null ? null : Math.max(0, Math.round(elapsed)))}</div>
        </div>
        <div className="kpi">
          <div className="label">Steps approved</div>
          <div className="value">{approved}<span className="faint" style={{ fontSize: 16 }}> / {run.order.length || "–"}</span></div>
        </div>
        <div className="kpi">
          <div className="label">Supervisor retries</div>
          <div className="value" style={{ color: retries ? "var(--warning)" : undefined }}>{retries}</div>
        </div>
        <div className="kpi">
          <div className="label">Tokens</div>
          <div className="value">{compact(tokens || run.events.filter((e) => e.type === "step.output").reduce((n, e) => n + (e.payload.tokens ?? 0), 0))}</div>
        </div>
      </div>

      <div className="run-grid">
        <div className="stack">
          <div className="panel">
            <div className="panel-head">
              <div className="label">Execution graph</div>
              {run.graphSummary && <span className="muted" style={{ fontSize: 13 }}>{run.graphSummary}</span>}
            </div>
            <DagView run={run} selected={step?.step_id ?? null} onSelect={(sid) => { setSelected(sid); setTab("step"); }} />
          </div>

          {run.report && <ReportView report={run.report} />}

          <div className="panel">
            <div className="tabs" role="tablist">
              {([
                ["step", "Step inspector", run.order.length],
                ["supervisor", "Supervisor log", run.verdicts.length],
                ["plans", "Plan versions", run.plans.length],
              ] as [Tab, string, number][]).map(([key, label, count]) => (
                <button key={key} role="tab" aria-selected={tab === key} className={`tab${tab === key ? " on" : ""}`} onClick={() => setTab(key)}>
                  {label} <span className="count">{count}</span>
                </button>
              ))}
            </div>

            {tab === "step" && (step ? <StepDetail step={step} /> : <div className="muted">Steps appear once the Supervisor approves a plan.</div>)}
            {tab === "supervisor" && <SupervisorLog run={run} />}
            {tab === "plans" && <PlanVersions plans={run.plans} />}
          </div>
        </div>

        <EventFeed run={run as RunState} connection={connection} />
      </div>
    </>
  );
}
