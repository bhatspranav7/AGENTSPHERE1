const FLOW = [
  ["Planner", "#67d4ea", "LLM turns the objective into JSON steps with dependencies."],
  ["Supervisor", "#f07878", "Validates schema, size and acyclicity. Rejects with feedback; falls back after the retry budget."],
  ["TaskGraph", "#b58cff", "Kahn topological sort. Ready steps run in parallel on a bounded pool."],
  ["Agents", "#7aa8ff", "Research, Code and Automation produce typed JSON using upstream outputs as context."],
  ["Supervisor", "#f07878", "Schema, hallucination markers, relevance, code/action checks + LLM judge → APPROVE / RETRY / ABORT."],
  ["Reporter", "#6fd49b", "Summarises approved outputs. Everything lands in Postgres; memory in Redis."],
];

const GUARANTEES = [
  ["LLM hallucinates", "Refusal/placeholder markers and relevance scoring reject the output; the agent retries with the Supervisor's feedback."],
  ["LLM breaks the JSON contract", "Pydantic schemas per agent. Invalid output never reaches a downstream agent."],
  ["Planner produces a cycle", "TaskGraph detects it, the Supervisor sends it back, and a deterministic fallback plan takes over if needed."],
  ["A step can't be fixed", "The retry budget is exhausted → ABORT. Siblings halt at their next checkpoint; unstarted steps are marked skipped."],
  ["LLM provider is down", "Retries with backoff on 429/5xx, then the step fails cleanly and is audited. The server never hangs."],
  ["Server restarts mid-run", "Runs left active are marked failed on boot. The event log survives, so the UI can still replay them."],
];

const STACK = [
  ["FastAPI", "REST + Server-Sent Events, API-key auth, per-IP rate limiting"],
  ["PostgreSQL", "execution_runs, execution_plans, agent_executions, supervisor_decisions, execution_events"],
  ["Redis", "Workflow memory and rate-limit windows (in-memory fallback)"],
  ["LLM layer", "Any OpenAI-compatible API (OpenAI, Groq, Ollama) or simulated mode"],
  ["React + Vite", "Live DAG, event stream, step inspector, insights"],
  ["Docker", "One image serves API + UI; Render blueprint for deploys"],
];

export default function Architecture() {
  return (
    <>
      <div className="page-head">
        <div>
          <div className="label">System design</div>
          <h1>In agentic AI, control matters more than intelligence.</h1>
          <p>
            The LLM proposes; the Supervisor disposes. Every plan and output is validated before anything downstream may
            use it, and every decision is persisted.
          </p>
        </div>
      </div>

      <div className="arch-flow">
        {FLOW.map(([name, color, text], i) => (
          <div key={i} className="panel arch-step" style={{ borderTop: `2px solid ${color}` }}>
            <div className="n" style={{ color }}>0{i + 1}</div>
            <h3>{name}</h3>
            <p>{text}</p>
          </div>
        ))}
      </div>

      <h2 className="h2">Failure modes it's built for</h2>
      <div className="grid-3">
        {GUARANTEES.map(([k, v]) => (
          <div key={k} className="panel">
            <b style={{ color: "var(--accent)" }}>{k}</b>
            <p className="muted" style={{ margin: "8px 0 0", fontSize: 14, lineHeight: 1.55 }}>{v}</p>
          </div>
        ))}
      </div>

      <h2 className="h2">Execution lifecycle</h2>
      <div className="panel mono" style={{ fontSize: 13, lineHeight: 2.2, overflowX: "auto", whiteSpace: "nowrap" }}>
        <span className="pill">queued</span> → <span className="pill info">planning</span> → <span className="pill info">running</span> →{" "}
        <span className="pill ok">completed</span>
        <br />
        <span className="muted">planning / running →</span> <span className="pill bad">aborted</span>{" "}
        <span className="muted">(supervisor)</span> · <span className="pill bad">failed</span> <span className="muted">(crash)</span> ·{" "}
        <span className="pill">cancelled</span> <span className="muted">(user)</span>
      </div>

      <h2 className="h2">Stack</h2>
      <div className="grid-3">
        {STACK.map(([k, v]) => (
          <div key={k} className="panel">
            <div className="label" style={{ color: "var(--accent)" }}>{k}</div>
            <p style={{ margin: "8px 0 0", fontSize: 14.5, lineHeight: 1.5 }}>{v}</p>
          </div>
        ))}
      </div>
    </>
  );
}
