import type { AgentName, Check, Decision, ExecEvent, PlanStep } from "./api";

export type NodeState = "pending" | "running" | "retrying" | "approved" | "failed" | "skipped";

export interface Verdict {
  target: "plan" | "step";
  step_id: number | null;
  attempt: number;
  decision: Decision;
  score: number;
  reason: string;
  feedback: string | null;
  checks: Check[];
  injected_fault: string | null;
  ts: string;
}

export interface Attempt {
  attempt: number;
  output?: Record<string, any>;
  latency_ms?: number;
  tokens?: number;
  injected_fault?: string | null;
  llm_error?: string | null;
  verdict?: Verdict;
}

export interface StepState extends PlanStep {
  state: NodeState;
  attempts: Attempt[];
  score?: number;
}

export interface PlanVersion {
  version: number;
  source: string;
  plan: { summary?: string; steps?: PlanStep[] };
  injected_fault: string | null;
  verdict?: Verdict;
}

export interface RunState {
  status: string;
  objective?: string;
  llmMode?: string;
  llmModel?: string;
  chaos?: string;
  planner: NodeState;
  reporter: NodeState;
  plans: PlanVersion[];
  graphSummary?: string;
  fallback: boolean;
  depth: number;
  steps: Record<number, StepState>;
  order: number[];
  verdicts: Verdict[];
  report?: Record<string, any>;
  stats?: { duration_ms: number; total_tokens: number; retries: number };
  reason?: string;
  events: ExecEvent[];
  startedAt?: string;
  endedAt?: string;
}

export const initialRun: RunState = {
  status: "queued",
  planner: "pending",
  reporter: "pending",
  plans: [],
  fallback: false,
  depth: 0,
  steps: {},
  order: [],
  verdicts: [],
  events: [],
};

function patchStep(s: RunState, id: number, fn: (st: StepState) => StepState): RunState {
  const cur = s.steps[id];
  if (!cur) return s;
  return { ...s, steps: { ...s.steps, [id]: fn(cur) } };
}

function upsertAttempt(st: StepState, n: number, patch: Partial<Attempt>): StepState {
  const attempts = [...st.attempts];
  const i = attempts.findIndex((a) => a.attempt === n);
  if (i === -1) attempts.push({ attempt: n, ...patch });
  else attempts[i] = { ...attempts[i], ...patch };
  return { ...st, attempts };
}

export function reduce(s: RunState, e: ExecEvent): RunState {
  if (s.events.some((x) => x.id === e.id)) return s;
  const p = e.payload;
  s = { ...s, events: [...s.events, e] };

  switch (e.type) {
    case "execution.queued":
      return { ...s, objective: p.objective, chaos: p.chaos };
    case "execution.started":
      return { ...s, status: "planning", objective: p.objective, chaos: p.chaos, llmMode: p.llm_mode,
               llmModel: p.llm_model, startedAt: e.ts };
    case "agent.started":
      if (p.agent === "planner") return { ...s, planner: "running" };
      if (p.agent === "reporter") return { ...s, reporter: "running" };
      return s;
    case "plan.proposed":
      return { ...s, plans: [...s.plans, { version: p.version, source: p.source, plan: p.plan,
                                           injected_fault: p.injected_fault }] };
    case "supervisor.decision": {
      const v: Verdict = { ...(p as any), ts: e.ts };
      s = { ...s, verdicts: [...s.verdicts, v] };
      if (v.target === "plan") {
        return {
          ...s,
          planner: v.decision === "APPROVE" ? "approved" : "retrying",
          plans: s.plans.map((pl) => (pl.version === v.attempt && !pl.verdict ? { ...pl, verdict: v } : pl)),
        };
      }
      return patchStep(s, v.step_id!, (st) => {
        const next = upsertAttempt(st, v.attempt, { verdict: v });
        return {
          ...next,
          score: v.score,
          state: v.decision === "APPROVE" ? "approved" : v.decision === "RETRY" ? "retrying" : "failed",
        };
      });
    }
    case "graph.ready": {
      const steps: Record<number, StepState> = {};
      for (const n of p.nodes as PlanStep[]) steps[n.step_id] = { ...n, state: "pending", attempts: [] };
      // Fallback plans skip the supervisor-approved path; mark planner done either way
      return { ...s, status: "running", planner: "approved", steps, order: (p.nodes as PlanStep[]).map((n) => n.step_id),
               depth: p.depth, graphSummary: p.summary, fallback: !!p.fallback };
    }
    case "step.started":
      return patchStep(s, p.step_id, (st) => ({ ...upsertAttempt(st, p.attempt, {}), state: "running" }));
    case "step.output":
      return patchStep(s, p.step_id, (st) =>
        upsertAttempt(st, p.attempt, { output: p.output, latency_ms: p.latency_ms, tokens: p.tokens,
                                       injected_fault: p.injected_fault, llm_error: p.llm_error }),
      );
    case "step.completed":
      return patchStep(s, p.step_id, (st) => ({ ...st, state: "approved", score: p.score }));
    case "step.failed":
      return patchStep(s, p.step_id, (st) => ({ ...st, state: "failed" }));
    case "step.skipped":
      return patchStep(s, p.step_id, (st) => ({ ...st, state: "skipped" }));
    case "report.ready":
      return { ...s, report: p.report, reporter: "approved" };
    case "execution.completed":
      return { ...s, status: "completed", report: p.report ?? s.report, reporter: "approved", stats: pickStats(p), endedAt: e.ts };
    case "execution.aborted":
    case "execution.failed":
    case "execution.cancelled": {
      const status = e.type.split(".")[1];
      // Anything still running when the run ended was stopped
      const steps = Object.fromEntries(
        Object.entries(s.steps).map(([k, st]) => [k, st.state === "running" || st.state === "pending" || st.state === "retrying"
          ? { ...st, state: "skipped" as NodeState } : st]),
      );
      return { ...s, status, steps, stats: pickStats(p), reason: p.reason, endedAt: e.ts,
               planner: s.planner === "running" ? "failed" : s.planner,
               reporter: s.reporter === "running" ? "failed" : s.reporter };
    }
    default:
      return s;
  }
}

function pickStats(p: Record<string, any>) {
  return p.duration_ms !== undefined
    ? { duration_ms: p.duration_ms, total_tokens: p.total_tokens, retries: p.retries }
    : undefined;
}

export const AGENT_COLORS: Record<AgentName | "planner" | "supervisor" | "reporter", string> = {
  planner: "#67d4ea",
  research: "#7aa8ff",
  code: "#b58cff",
  automation: "#f2c14e",
  supervisor: "#f07878",
  reporter: "#6fd49b",
};
