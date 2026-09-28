# AgentSphere

**Autonomous multi-agent workflow system.** Give it one objective. A Planner turns it into a dependency graph, specialist agents run it in parallel, and a **Supervisor** approves, retries or aborts every single output. Every plan, attempt and verdict is persisted and replayable.

![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white) ![React](https://img.shields.io/badge/React-20232a?logo=react&logoColor=61dafb) ![PostgreSQL](https://img.shields.io/badge/PostgreSQL-4169e1?logo=postgresql&logoColor=white) ![Redis](https://img.shields.io/badge/Redis-dc382d?logo=redis&logoColor=white) ![Docker](https://img.shields.io/badge/Docker-2496ed?logo=docker&logoColor=white)

> *In agentic AI, control matters more than intelligence.* The LLM proposes; the Supervisor disposes.

```
                      ┌──────────── Supervisor (validates, feedback, retry budget) ────────────┐
                      ▼                                                                         │
Objective ─► Planner ─► TaskGraph (DAG) ─┬─► Research ─┐                                        │
             (LLM, JSON)   Kahn topo sort ├─► Research ─┼─► Code ─┬─► Automation ─┐              │
                                          │             │         └─► Automation ─┼─► Reporter ─┘
                                          └─ ready steps run in parallel ─────────┘
        PostgreSQL: runs · plans · agent attempts · supervisor decisions · event log      Redis: workflow memory · rate limits
```

## What makes it interesting

| | |
|---|---|
| **DAG orchestration** | The plan is validated as an acyclic graph (Kahn's algorithm). Steps start the moment their dependencies are approved, so independent work runs concurrently. |
| **Supervisor guardrails** | Pydantic contracts per agent, hallucination/refusal markers, relevance scoring, code and action checks, plus an LLM-as-judge in live mode. It decides **APPROVE / RETRY (with feedback) / ABORT**. |
| **Chaos engineering** | Launch with `chaos: "retry"` to inject a cyclic plan and hallucinated outputs, which the Supervisor catches and recovers from. `chaos: "abort"` makes one agent fail on every attempt, so you can watch a safe abort that halts sibling steps. |
| **Planner fallback** | If the planner can't produce an approvable plan within its retry budget, a deterministic fallback plan takes over, so the run never dead-ends. |
| **Live streaming** | Server-Sent Events backed by an append-only `execution_events` table: join mid-run or after completion and replay everything, with `Last-Event-ID` resume. |
| **Full audit trail** | `execution_runs`, `execution_plans` (every version), `agent_executions` (every attempt), `supervisor_decisions` (every verdict, with checks and scores). |
| **Any LLM** | Any OpenAI-compatible API (OpenAI, Groq, Ollama `/v1`, OpenRouter). With no key it runs a clearly-labelled **simulated** mode, so the platform is demoable for free. |
| **Production basics** | API-key auth (constant-time compare), a rate-limited public demo key, bounded worker pool, cancellation, crash recovery on boot, in-place schema upgrades from v1. |

## The UI

- **Launch.** One-line mission composer with chaos modes.
- **Run view.** A live DAG (running / retrying / approved / aborted nodes and animated edges), the SSE event stream, a step inspector with every attempt's output (findings, generated code with syntax highlighting, executed actions) and its Supervisor verdict, the Supervisor log, plan versions, and the final report.
- **Runs.** A searchable, filterable audit trail.
- **Insights.** Success rate, latency, verdict mix, runs per day, and per-agent approval rate and latency.
- **Crew / Architecture.** The agent registry and the system design.

## Run it

### Docker (everything)

```bash
docker compose up --build
```

- UI: http://localhost:8000
- Swagger: http://localhost:8000/docs
- The admin key is `agentsphere-dev-key`. The UI uses the demo key automatically.

Use `APP_PORT=8001 docker compose up` if port 8000 is taken. For a real LLM, export `LLM_API_KEY` (plus `LLM_BASE_URL` / `LLM_MODEL`) before starting.

### Local development (WSL)

```bash
cd ~/AGENTSPHERE1
python3 -m venv backend/venv && source backend/venv/bin/activate
pip install -r backend/requirements.txt
cp backend/.env.example .env             # edit DATABASE_URL etc.
uvicorn backend.app.main:app --reload    # http://127.0.0.1:8000/docs

cd frontend && npm install && npm run dev   # http://localhost:5173 (proxies /api)
```

Tables are created, and older v1 tables are upgraded in place, on startup.

## API

Every route is served at the root and under `/api`. Protected routes need `X-API-Key`.

```bash
# start (async) and follow live
curl -X POST localhost:8000/executions -H "X-API-Key: agentsphere-dev-key" \
     -H "Content-Type: application/json" -d '{"user_objective":"hospital emergency workflow","chaos":"retry"}'
curl -N localhost:8000/executions/<id>/stream -H "X-API-Key: agentsphere-dev-key"

# v1-compatible: blocks until done
curl -X POST localhost:8000/executions/start -H "X-API-Key: agentsphere-dev-key" \
     -H "Content-Type: application/json" -d '{"user_objective":"hospital ambulance workflow"}'
```

| Method | Path | |
|---|---|---|
| POST | `/executions` | Queue a run → `202` |
| POST | `/executions/start` | v1: run and wait (`?wait=false` to return immediately) |
| GET | `/executions` | List (`limit`, `offset`, `status`, `q`) |
| GET | `/executions/{id}` | Full audit: plans, attempts, verdicts, report |
| GET | `/executions/{id}/stream` | SSE: replay + live |
| GET | `/executions/{id}/events` | Event log (`after=`) |
| POST | `/executions/{id}/cancel` | Cancel a queued or running run |
| POST | `/executions/{id}/replay` | Re-run as a new, linked execution |
| GET | `/metrics`, `/agents` | Insights |
| GET | `/health`, `/config/public` | Public |

## Configuration

| Variable | Default | |
|---|---|---|
| `DATABASE_URL` | `postgresql://agentsphere:agentsphere@localhost:5432/agentsphere_db` | `postgres://` accepted |
| `REDIS_URL` | `redis://localhost:6379/0` | Optional; falls back to in-memory |
| `API_KEY` / `API_KEYS` | `agentsphere-dev-key` | Admin key(s), comma-separated |
| `DEMO_API_KEY` | empty | Public key the UI auto-uses, rate limited per IP |
| `DEMO_RATE_LIMIT_PER_HOUR` | `20` | |
| `LLM_BASE_URL` / `LLM_API_KEY` / `LLM_MODEL` | OpenAI / empty / `gpt-4o-mini` | Empty key → simulated mode |
| `LLM_MODE` | `auto` | `auto`, `live`, or `simulated` |
| `MAX_STEP_RETRIES` / `MAX_PLAN_RETRIES` | `2` / `2` | Supervisor retry budgets |
| `STEP_PARALLELISM` / `WORKER_THREADS` | `3` / `4` | Concurrency limits |

## Deploy (Render)

1. Create a free Postgres at [neon.tech](https://neon.tech) and copy its connection string. Render allows only one free Postgres per account.
2. On Render, go to **New → Blueprint** and pick this repo. When prompted, paste the Neon URL into `DATABASE_URL`.
3. Optional: add a [Groq](https://console.groq.com) key as `LLM_API_KEY` for a real, free LLM. Otherwise it runs in simulated mode.

## Project layout

```
backend/app/
  agents/        planner, research, code, automation, reporter + supervisor (guardrails)
  orchestrator/  task_graph (DAG) · engine (plan → parallel execution → report, chaos, cancel)
  llm/           OpenAI-compatible client · simulated backend
  services/      event bus (DB + SSE fan-out) · runner (worker pool, recovery)
  api/           executions (REST + SSE) · system (health, metrics, agents)
  models/ db/ core/ schemas.py
frontend/src/    React + Vite + TS (live DAG, event feed, inspector, insights)
```
