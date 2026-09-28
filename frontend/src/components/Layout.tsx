import { useState, type FormEvent, type ReactNode } from "react";
import { NavLink } from "react-router-dom";
import { useApp } from "../app-context";
import { IconArch, IconChart, IconCrew, IconKey, IconLaunch, IconRuns } from "./icons";

const LINKS = [
  { to: "/", label: "Launch", icon: IconLaunch, end: true },
  { to: "/runs", label: "Runs", icon: IconRuns },
  { to: "/insights", label: "Insights", icon: IconChart },
  { to: "/crew", label: "Agent crew", icon: IconCrew },
  { to: "/architecture", label: "Architecture", icon: IconArch },
];

export function Layout({ children }: { children: ReactNode }) {
  const { health, keySource, openKeyDialog, keyDialog } = useApp();

  return (
    <div className="app">
      <aside className="sidebar">
        <NavLink to="/" className="brand">
          <span className="orb" />
          <span>
            AgentSphere
            <small>Autonomous agents</small>
          </span>
        </NavLink>

        <nav className="nav">
          {LINKS.map(({ to, label, icon: Icon, end }) => (
            <NavLink key={to} to={to} end={end}>
              <Icon /> {label}
            </NavLink>
          ))}
        </nav>

        <div className="sidebar-foot">
          <button className="btn sm ghost" onClick={() => openKeyDialog(true)} style={{ justifyContent: "flex-start" }}>
            <IconKey /> {keySource === "demo" ? "Demo key" : keySource ? "API key set" : "Set API key"}
          </button>
          <a className="btn sm ghost" href="/docs" target="_blank" rel="noreferrer" style={{ justifyContent: "flex-start" }}>
            ⌘ API docs
          </a>
        </div>
      </aside>

      <nav className="mobile-nav">
        {LINKS.map(({ to, label, end }) => (
          <NavLink key={to} to={to} end={end}>
            {label}
          </NavLink>
        ))}
        <button className="btn sm ghost" onClick={() => openKeyDialog(true)}>Key</button>
      </nav>

      <main className="main">
        <div className="topbar">
          {health ? (
            <>
              <span className={`pill ${health.database === "reachable" ? "ok" : "bad"}`}>
                <span className="dot" /> postgres
              </span>
              <span className={`pill ${health.cache === "redis" ? "ok" : "warn"}`}>
                <span className="dot" /> {health.cache}
              </span>
              <span className={`pill ${health.llm_mode === "live" ? "violet" : "info"}`} title={health.llm_model}>
                <span className="dot" /> LLM · {health.llm_mode === "live" ? health.llm_model : "simulated"}
              </span>
              {health.active_executions > 0 && (
                <span className="pill info live">
                  <span className="dot" /> {health.active_executions} running
                </span>
              )}
            </>
          ) : (
            <span className="pill bad">
              <span className="dot" /> API offline
            </span>
          )}
        </div>
        {children}
      </main>

      {keyDialog && <KeyDialog />}
    </div>
  );
}

function KeyDialog() {
  const { apiKey, setApiKey, openKeyDialog, config, toast } = useApp();
  const [value, setValue] = useState(apiKey ?? "");

  const submit = (e: FormEvent) => {
    e.preventDefault();
    setApiKey(value.trim() || null);
    openKeyDialog(false);
    toast("API key saved in this browser", "ok");
  };

  return (
    <div className="overlay" onClick={() => openKeyDialog(false)}>
      <form className="panel dialog" onSubmit={submit} onClick={(e) => e.stopPropagation()}>
        <div className="label">Authentication</div>
        <h2 style={{ margin: "8px 0 6px", fontSize: 22 }}>API key</h2>
        <p className="muted" style={{ margin: "0 0 16px", fontSize: 14, lineHeight: 1.5 }}>
          Every execution endpoint requires an <span className="mono">X-API-Key</span>. It's stored only in this browser.
          {config?.demo_api_key && (
            <> A public demo key is available, limited to {config.demo_rate_limit_per_hour} runs per hour.</>
          )}
        </p>
        <input
          className="input mono"
          style={{ width: "100%" }}
          value={value}
          onChange={(e) => setValue(e.target.value)}
          placeholder="agentsphere-dev-key"
          autoFocus
        />
        <div style={{ display: "flex", gap: 8, marginTop: 16, flexWrap: "wrap" }}>
          <button className="btn primary">Save key</button>
          {config?.demo_api_key && (
            <button type="button" className="btn" onClick={() => setValue(config.demo_api_key!)}>
              Use demo key
            </button>
          )}
          <button type="button" className="btn ghost" onClick={() => openKeyDialog(false)}>
            Cancel
          </button>
        </div>
      </form>
    </div>
  );
}
