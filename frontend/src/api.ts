const API = `${(import.meta.env.VITE_API_URL ?? "").replace(/\/$/, "")}/api`;
const KEY_STORAGE = "agentsphere.apiKey";

export type RunStatus = "queued" | "planning" | "running" | "completed" | "failed" | "aborted" | "cancelled";
export type Chaos = "off" | "retry" | "abort";
export type AgentName = "research" | "code" | "automation";
export type Decision = "APPROVE" | "RETRY" | "ABORT";

export const TERMINAL: RunStatus[] = ["completed", "failed", "aborted", "cancelled"];

export interface Run {
  execution_id: string;
  objective: string | null;
  status: RunStatus;
  phase: string | null;
  llm_mode: string | null;
  llm_model: string | null;
  chaos: Chaos;
  parent_id: string | null;
  error: string | null;
  total_tokens: number;
  retries: number;
  duration_ms: number | null;
  created_at: string | null;
  started_at: string | null;
  finished_at: string | null;
}

export interface PlanStep {
  step_id: number;
  agent: AgentName;
  title: string;
  objective: string;
  depends_on: number[];
  expected_output: string;
  level?: number;
}

export interface Check {
  name: string;
  passed: boolean;
  detail?: unknown;
}

export interface ExecEvent {
  id: number;
  execution_id: string;
  type: string;
  payload: Record<string, any>;
  ts: string;
}

export interface Health {
  status: string;
  database: string;
  cache: string;
  llm_mode: string;
  llm_model: string;
  active_executions: number;
}

export interface PublicConfig {
  demo_api_key: string | null;
  demo_rate_limit_per_hour: number;
  llm_mode: string;
  llm_model: string;
  max_step_retries: number;
  max_plan_retries: number;
  step_parallelism: number;
}

export interface AgentStat {
  name: string;
  role: string;
  description: string;
  color: string;
  attempts: number;
  approval_rate: number | null;
  avg_latency_ms: number | null;
  tokens: number;
}

export interface Metrics {
  total_executions: number;
  by_status: Record<string, number>;
  success_rate: number | null;
  avg_duration_ms: number | null;
  p95_duration_ms: number | null;
  total_tokens: number;
  total_retries: number;
  supervisor_decisions: Record<string, number>;
  daily: ({ date: string } & Record<string, number | string>)[];
  active_executions: number;
}

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

export const keyStore = {
  get(): string | null {
    try {
      return localStorage.getItem(KEY_STORAGE);
    } catch {
      return null;
    }
  },
  set(key: string | null) {
    try {
      if (key) localStorage.setItem(KEY_STORAGE, key);
      else localStorage.removeItem(KEY_STORAGE);
    } catch {
      /* storage blocked: key lives for this page only */
    }
    runtimeKey = key;
  },
};

let runtimeKey: string | null = keyStore.get();
export const currentKey = () => runtimeKey;

function detailMessage(body: any, fallback: string): string {
  const d = body?.detail;
  if (typeof d === "string") return d;
  if (d?.error) return String(d.error);
  if (Array.isArray(d)) return d.map((x) => x?.msg ?? String(x)).join(", ");
  return fallback;
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  if (runtimeKey) headers.set("X-API-Key", runtimeKey);
  if (init.body) headers.set("Content-Type", "application/json");

  let res: Response;
  try {
    res = await fetch(`${API}${path}`, { ...init, headers });
  } catch {
    throw new ApiError(0, "Cannot reach the AgentSphere API");
  }
  const body = await res.json().catch(() => null);
  if (!res.ok) throw new ApiError(res.status, detailMessage(body, `Request failed (${res.status})`));
  return body as T;
}

const post = <T>(path: string, body?: unknown) =>
  request<T>(path, { method: "POST", body: body === undefined ? undefined : JSON.stringify(body) });

export const api = {
  health: () => request<Health>("/health"),
  config: () => request<PublicConfig>("/config/public"),
  agents: () => request<AgentStat[]>("/agents"),
  metrics: () => request<Metrics>("/metrics"),
  runs: (params: { limit?: number; offset?: number; status?: string; q?: string } = {}) => {
    const qs = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => v !== undefined && v !== "" && qs.set(k, String(v)));
    return request<{ total: number; items: Run[] }>(`/executions?${qs}`);
  },
  run: (id: string) => request<Run & Record<string, any>>(`/executions/${id}`),
  start: (user_objective: string, chaos: Chaos) => post<Run>("/executions", { user_objective, chaos }),
  cancel: (id: string) => post<{ status: string }>(`/executions/${id}/cancel`),
  replay: (id: string) => post<Run>(`/executions/${id}/replay`),
};

/**
 * Server-Sent Events over fetch (so the API key travels in a header, not the URL).
 * Reconnects with Last-Event-ID so no event is lost or duplicated.
 */
export function streamEvents(
  id: string,
  onEvent: (e: ExecEvent) => void,
  onState: (s: "connecting" | "live" | "closed") => void,
): () => void {
  const controller = new AbortController();
  let lastId = 0;
  let finished = false;

  const run = async () => {
    for (let attempt = 0; !controller.signal.aborted && !finished; attempt++) {
      onState("connecting");
      try {
        const headers: Record<string, string> = {};
        if (runtimeKey) headers["X-API-Key"] = runtimeKey;
        if (lastId) headers["Last-Event-ID"] = String(lastId);
        const res = await fetch(`${API}/executions/${id}/stream`, { headers, signal: controller.signal });
        if (!res.ok || !res.body) throw new ApiError(res.status, "stream failed");
        onState("live");

        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";
        for (;;) {
          const { value, done } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true });
          let idx;
          while ((idx = buffer.indexOf("\n\n")) !== -1) {
            const frame = buffer.slice(0, idx);
            buffer = buffer.slice(idx + 2);
            const data = frame
              .split("\n")
              .filter((l) => l.startsWith("data:"))
              .map((l) => l.slice(5).trim())
              .join("\n");
            if (!data) continue;
            const event = JSON.parse(data) as ExecEvent;
            lastId = event.id;
            onEvent(event);
            if (TERMINAL_EVENT_TYPES.has(event.type)) finished = true;
          }
        }
        if (finished) break;
      } catch (e) {
        if (controller.signal.aborted) break;
        if (e instanceof ApiError && (e.status === 401 || e.status === 404)) break;
      }
      await new Promise((r) => setTimeout(r, Math.min(1000 * 2 ** attempt, 8000)));
    }
    onState("closed");
  };

  run();
  return () => controller.abort();
}

export const TERMINAL_EVENT_TYPES = new Set([
  "execution.completed",
  "execution.failed",
  "execution.aborted",
  "execution.cancelled",
]);
