import { useEffect, useState } from "react";
import { api, type AgentStat } from "../api";
import { useApp } from "../app-context";
import { IconBolt, IconBrain, IconCode, IconDoc, IconGraph, IconShield } from "../components/icons";
import { compact, duration, pct } from "../format";

const ICONS: Record<string, typeof IconBolt> = {
  planner: IconGraph,
  research: IconBrain,
  code: IconCode,
  automation: IconBolt,
  supervisor: IconShield,
  reporter: IconDoc,
};

export default function Crew() {
  const { apiKey } = useApp();
  const [agents, setAgents] = useState<AgentStat[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (apiKey) api.agents().then(setAgents).catch((e) => setError(e.message));
  }, [apiKey]);

  return (
    <>
      <div className="page-head">
        <div>
          <div className="label">Agent registry</div>
          <h1>The crew</h1>
          <p>Six specialised agents. Three do the work, one plans it, one polices it, and one reports on it.</p>
        </div>
      </div>
      {error && <p className="error">{error}</p>}
      {!agents ? (
        <div className="skeleton" style={{ minHeight: 240 }} />
      ) : (
        <div className="crew">
          {agents.map((a) => {
            const Icon = ICONS[a.name] ?? IconBolt;
            const worker = ["research", "code", "automation"].includes(a.name);
            return (
              <div key={a.name} className="panel crew-card">
                <div className="avatar" style={{ background: `${a.color}1f`, color: a.color, boxShadow: `inset 0 0 0 1px ${a.color}55` }}>
                  <Icon />
                </div>
                <div className="label" style={{ color: a.color }}>{a.role}</div>
                <h3>{a.name}</h3>
                <p>{a.description}</p>
                {worker ? (
                  <div className="crew-stats">
                    <div><span className="label">Attempts</span><b>{compact(a.attempts)}</b></div>
                    <div><span className="label">Approved</span><b>{pct(a.approval_rate)}</b></div>
                    <div><span className="label">Latency</span><b>{duration(a.avg_latency_ms)}</b></div>
                  </div>
                ) : (
                  <div className="crew-stats" style={{ gridTemplateColumns: "1fr" }}>
                    <span className="faint" style={{ fontSize: 13 }}>
                      {a.name === "supervisor" ? "Reviews every plan and output: schema, DAG, hallucination, relevance, LLM judge."
                        : a.name === "planner" ? "Output is validated as a DAG before anything runs."
                        : "Runs once all steps are approved."}
                    </span>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </>
  );
}
