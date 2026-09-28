import { useEffect, useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api, type Chaos, type Run } from "../api";
import { useApp } from "../app-context";
import { IconBolt, IconDb, IconGraph, IconLaunch, IconShield } from "../components/icons";
import { RunStatusPill } from "../components/Status";
import { ago, duration } from "../format";

const EXAMPLES = [
  "Automate the hospital emergency ambulance dispatch workflow",
  "Invoice approval and payment reconciliation for finance",
  "Employee onboarding with laptop and access provisioning",
  "Incident response for a Kubernetes production outage",
  "Order fulfilment with inventory sync and refunds",
];

const CHAOS: { value: Chaos; label: string; hint: string }[] = [
  { value: "off", label: "Clean run", hint: "No injected faults" },
  { value: "retry", label: "Recoverable faults", hint: "Bad plan + hallucinated outputs. Watch the Supervisor retry them." },
  { value: "abort", label: "Fatal fault", hint: "One agent keeps failing. Watch the Supervisor abort safely." },
];

export default function Launch() {
  const navigate = useNavigate();
  const { apiKey, openKeyDialog, toast, config } = useApp();
  const [objective, setObjective] = useState("");
  const [chaos, setChaos] = useState<Chaos>("off");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [recent, setRecent] = useState<Run[] | null>(null);

  useEffect(() => {
    if (!apiKey) return;
    api.runs({ limit: 5 }).then((r) => setRecent(r.items)).catch(() => setRecent([]));
  }, [apiKey]);

  const launch = async (e?: FormEvent) => {
    e?.preventDefault();
    if (!apiKey) return openKeyDialog(true);
    if (objective.trim().length < 5) return setError("Describe the objective in a few words.");
    setBusy(true);
    setError(null);
    try {
      const run = await api.start(objective.trim(), chaos);
      navigate(`/runs/${run.execution_id}`);
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Launch failed";
      setError(msg);
      toast(msg, "err");
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      <section className="hero">
        <span className="pill info"><span className="dot" /> Planner → DAG → Agents ⇄ Supervisor → Report</span>
        <h1>
          One instruction.<br />
          <span className="gradient-text">A whole crew of agents</span> gets it done.
        </h1>
        <p>
          AgentSphere plans your objective into a dependency graph, runs specialist agents in parallel, and puts every
          output through a Supervisor that approves, retries or aborts. Every step is persisted and replayable.
        </p>

        <form className="composer" onSubmit={launch}>
          <div className="composer-inner">
            <label className="label" htmlFor="objective">Mission objective</label>
            <textarea
              id="objective"
              value={objective}
              maxLength={500}
              onChange={(e) => setObjective(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) launch();
              }}
              placeholder="e.g. Automate the hospital emergency ambulance dispatch workflow"
            />
            <div className="composer-foot">
              <div className="segmented" role="radiogroup" aria-label="Chaos mode">
                {CHAOS.map((c) => (
                  <button key={c.value} type="button" role="radio" aria-checked={chaos === c.value}
                          className={chaos === c.value ? "on" : ""} onClick={() => setChaos(c.value)} title={c.hint}>
                    {c.label}
                  </button>
                ))}
              </div>
              <span className="muted" style={{ fontSize: 13, flex: 1, minWidth: 160 }}>
                {CHAOS.find((c) => c.value === chaos)!.hint}
              </span>
              <button className="btn primary lg" disabled={busy}>
                <IconLaunch /> {busy ? "Launching…" : "Launch agents"}
              </button>
            </div>
          </div>
        </form>
        {error && <p className="error">{error}</p>}

        <div className="chips">
          {EXAMPLES.map((x) => (
            <button key={x} className="chip" onClick={() => setObjective(x)}>{x}</button>
          ))}
        </div>
      </section>

      <div className="feature-row">
        {[
          { Icon: IconGraph, color: "#67d4ea", t: "DAG orchestration", d: "Independent steps run in parallel as soon as their dependencies finish." },
          { Icon: IconShield, color: "#f07878", t: "Supervisor guardrails", d: "Schema, hallucination and relevance checks. Approve, retry with feedback, or abort." },
          { Icon: IconBolt, color: "#f2c14e", t: "Chaos engineering", d: "Inject bad plans and hallucinations on purpose to prove the system recovers." },
          { Icon: IconDb, color: "#6fd49b", t: "Full audit trail", d: "Plans, attempts, verdicts and events in Postgres. Replay any run." },
        ].map(({ Icon, color, t, d }) => (
          <div key={t} className="feature">
            <span className="icon" style={{ background: `${color}22`, color }}><Icon /></span>
            <b>{t}</b>
            <span>{d}</span>
          </div>
        ))}
      </div>

      <div className="panel" style={{ padding: "18px 4px 4px" }}>
        <div className="panel-head" style={{ padding: "0 16px" }}>
          <div className="label">Recent executions</div>
          <Link to="/runs" className="btn sm ghost">View all →</Link>
        </div>
        {!apiKey ? (
          <div className="empty">Set an API key to see executions.</div>
        ) : recent === null ? (
          <div className="skeleton" style={{ margin: 16 }} />
        ) : recent.length === 0 ? (
          <div className="empty">No executions yet. Launch your first mission above.</div>
        ) : (
          recent.map((r) => (
            <Link key={r.execution_id} to={`/runs/${r.execution_id}`} className="run-row">
              <RunStatusPill status={r.status} />
              <span className="objective">{r.objective}</span>
              <span className="num">{duration(r.duration_ms)}</span>
              <span className="num">{r.retries} retries</span>
              <span className="num">{r.chaos !== "off" ? `chaos:${r.chaos}` : ""}</span>
              <span className="num">{ago(r.created_at)}</span>
            </Link>
          ))
        )}
      </div>
      {config && config.llm_mode !== "live" && (
        <p className="faint" style={{ fontSize: 12.5, marginTop: 14 }}>
          This deployment runs in <b>simulated LLM mode</b>: agents produce deterministic, domain-templated output so the
          orchestration can be demoed for free. Set <span className="mono">LLM_API_KEY</span> to use a real model.
        </p>
      )}
    </>
  );
}
