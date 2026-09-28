import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, type Run } from "../api";
import { useApp } from "../app-context";
import { IconSearch } from "../components/icons";
import { RunStatusPill } from "../components/Status";
import { ago, compact, duration } from "../format";

const PAGE = 20;
const STATUSES = ["", "running", "completed", "aborted", "failed", "cancelled", "queued"];

export default function Runs() {
  const { apiKey } = useApp();
  const [items, setItems] = useState<Run[] | null>(null);
  const [total, setTotal] = useState(0);
  const [status, setStatus] = useState("");
  const [q, setQ] = useState("");
  const [query, setQuery] = useState("");
  const [page, setPage] = useState(0);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const t = window.setTimeout(() => {
      setQuery(q);
      setPage(0);
    }, 250);
    return () => window.clearTimeout(t);
  }, [q]);

  useEffect(() => {
    if (!apiKey) return;
    let alive = true;
    const load = () =>
      api
        .runs({ limit: PAGE, offset: page * PAGE, status, q: query })
        .then((r) => {
          if (!alive) return;
          setItems(r.items);
          setTotal(r.total);
          setError(null);
        })
        .catch((e) => alive && setError(e.message));
    load();
    const t = window.setInterval(load, 5000);
    return () => {
      alive = false;
      window.clearInterval(t);
    };
  }, [apiKey, page, status, query]);

  return (
    <>
      <div className="page-head">
        <div>
          <div className="label">Audit trail</div>
          <h1>Executions</h1>
          <p>Every run is persisted with its plan versions, agent attempts and supervisor verdicts. Open one to replay it.</p>
        </div>
        <Link to="/" className="btn primary">+ New mission</Link>
      </div>

      <div className="toolbar">
        <label style={{ position: "relative", flex: "1 1 260px", display: "flex" }}>
          <IconSearch width={15} height={15} style={{ position: "absolute", left: 11, top: 11, color: "var(--faint)" }} />
          <input className="input" style={{ paddingLeft: 34, width: "100%" }} placeholder="Search objectives…"
                 value={q} onChange={(e) => setQ(e.target.value)} aria-label="Search objectives" />
        </label>
        <select className="input" value={status} onChange={(e) => { setStatus(e.target.value); setPage(0); }} aria-label="Filter by status">
          {STATUSES.map((s) => <option key={s} value={s}>{s ? s[0].toUpperCase() + s.slice(1) : "All statuses"}</option>)}
        </select>
      </div>

      {error && <p className="error">{error}</p>}

      <div className="panel" style={{ padding: "16px 4px 4px" }}>
        <div className="run-row head">
          <span>Status</span><span>Objective</span><span>Duration</span><span>Retries</span><span>Tokens</span><span>Created</span>
        </div>
        {items === null ? (
          <div className="skeleton" style={{ margin: 16 }} />
        ) : items.length === 0 ? (
          <div className="empty">No executions match.</div>
        ) : (
          items.map((r) => (
            <Link key={r.execution_id} to={`/runs/${r.execution_id}`} className="run-row">
              <RunStatusPill status={r.status} />
              <span className="objective">
                {r.objective}
                {r.chaos !== "off" && <span className="pill warn" style={{ marginLeft: 8, padding: "1px 7px" }}>chaos:{r.chaos}</span>}
              </span>
              <span className="num">{duration(r.duration_ms)}</span>
              <span className="num">{r.retries}</span>
              <span className="num">{compact(r.total_tokens)}</span>
              <span className="num">{ago(r.created_at)}</span>
            </Link>
          ))
        )}
      </div>

      {total > PAGE && (
        <div style={{ display: "flex", gap: 8, alignItems: "center", justifyContent: "flex-end", marginTop: 14 }}>
          <span className="num">{page * PAGE + 1}–{Math.min(total, (page + 1) * PAGE)} of {total}</span>
          <button className="btn sm" disabled={page === 0} onClick={() => setPage(page - 1)}>← Prev</button>
          <button className="btn sm" disabled={(page + 1) * PAGE >= total} onClick={() => setPage(page + 1)}>Next →</button>
        </div>
      )}
    </>
  );
}
