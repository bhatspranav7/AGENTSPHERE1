"""Orchestrator: Planner → Supervisor → TaskGraph → Agents ⇄ Supervisor → Reporter.

One Orchestrator drives one execution on a worker thread. Independent steps
of the DAG run concurrently; every step loops agent → supervisor until it is
approved, its retry budget runs out (ABORT), or the run is cancelled.
"""
import random
import threading
import time
import uuid
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from datetime import datetime

from ..agents import EXECUTION_AGENTS, PlannerAgent, ReporterAgent
from ..agents.supervisor import ABORT, APPROVE, SupervisorAgent, Verdict
from ..core.cache import recall, remember
from ..core.config import settings
from ..core.exceptions import ExecutionAborted, ExecutionCancelled, LLMError
from ..core.logging import get_logger
from ..db.session import SessionLocal
from ..llm import get_llm
from ..models import AgentExecution, ExecutionPlan, ExecutionRun, ExecutionStatus, SupervisorDecision
from ..schemas import FinalReport, PlanStep
from ..services.events import bus
from .task_graph import TaskGraph

HALLUCINATION = "As an AI language model I cannot access real systems. TODO: placeholder output goes here."


class Orchestrator:
    def __init__(self, execution_id: uuid.UUID, objective: str, chaos: str, cancel_event: threading.Event):
        self.execution_id = execution_id
        self.objective = objective
        self.chaos = chaos
        self.cancelled = cancel_event
        self.halted = threading.Event()  # set when a sibling step aborts the run
        self.log = get_logger(str(execution_id))
        self.supervisor = SupervisorAgent()
        self.rng = random.Random(str(execution_id))
        self.faults: dict[int, str] = {}
        self._stats_lock = threading.Lock()
        self.tokens = 0
        self.retries = 0

    # -------------------------------------------------
    # LIFECYCLE
    # -------------------------------------------------
    def run(self):
        started = time.perf_counter()
        llm = get_llm()
        try:
            self._check_cancel()
            self._update(status=ExecutionStatus.PLANNING, phase="planning", started_at=datetime.utcnow(),
                         llm_mode=llm.mode, llm_model=llm.model)
            self._emit("execution.started", {"objective": self.objective, "chaos": self.chaos,
                                             "llm_mode": llm.mode, "llm_model": llm.model})

            graph = self._plan()

            self._update(status=ExecutionStatus.RUNNING, phase="executing")
            results = self._execute(graph)

            self._update(phase="reporting")
            report = self._report(graph, results)

            self._finish(ExecutionStatus.COMPLETED, started, result={"report": report})
            self._emit("execution.completed", {"report": report, **self._stats(started)})

        except ExecutionCancelled:
            self._finish(ExecutionStatus.CANCELLED, started, error="Cancelled by user")
            self._emit("execution.cancelled", self._stats(started))
        except ExecutionAborted as e:
            self._finish(ExecutionStatus.ABORTED, started, error=str(e))
            self._emit("execution.aborted", {"reason": str(e), **self._stats(started)})
        except Exception as e:
            self.log.exception("Execution crashed")
            self._finish(ExecutionStatus.FAILED, started, error=f"{type(e).__name__}: {e}")
            self._emit("execution.failed", {"reason": str(e), **self._stats(started)})

    # -------------------------------------------------
    # PLANNING
    # -------------------------------------------------
    def _plan(self) -> TaskGraph:
        planner = PlannerAgent()
        feedback = None

        for attempt in range(1, settings.MAX_PLAN_RETRIES + 2):
            self._check_cancel()
            self._emit("agent.started", {"agent": "planner", "attempt": attempt})

            try:
                resp = planner.run(self.objective, feedback, attempt)
                plan, error = resp.data, None
                self._add(tokens=resp.tokens)
            except LLMError as e:
                plan, error = {}, str(e)

            fault = None
            if self.chaos == "retry" and attempt == 1 and plan.get("steps"):
                plan, fault = self._corrupt_plan(plan), "dependency_cycle"

            verdict, validated, graph = self.supervisor.review_plan(plan, attempt)
            self._record_plan(attempt, plan, llm_source(), verdict, fault, error)

            if verdict.decision == APPROVE:
                self._emit("graph.ready", {**graph.to_dict(), "version": attempt, "summary": validated.summary})
                return graph
            if verdict.decision == ABORT:
                break
            self._add(retries=1)
            feedback = verdict.feedback

        # Never fail the run just because planning failed: fall back to a safe template
        self.log.warning("Planner exhausted retries - using fallback plan")
        plan = fallback_plan(self.objective)
        verdict, validated, graph = self.supervisor.review_plan(plan, 1)
        self._record_plan(settings.MAX_PLAN_RETRIES + 2, plan, "fallback", verdict, None, None)
        self._emit("graph.ready", {**graph.to_dict(), "version": settings.MAX_PLAN_RETRIES + 2,
                                   "summary": validated.summary, "fallback": True})
        return graph

    def _record_plan(self, version, plan, source, verdict: Verdict, fault, error):
        failed = [c for c in verdict.checks if not c["passed"]]
        self._save(
            ExecutionPlan(execution_id=self.execution_id, version=version, plan_json=plan, source=source,
                          approved=verdict.decision == APPROVE, validation_errors=failed or None,
                          created_at=datetime.utcnow()),
            SupervisorDecision(execution_id=self.execution_id, target="plan", attempt=version,
                               decision=verdict.decision, reason=verdict.reason, score=verdict.score,
                               decision_metadata={"checks": verdict.checks, "feedback": verdict.feedback,
                                                  "injected_fault": fault, "llm_error": error},
                               created_at=datetime.utcnow()),
        )
        self._emit("plan.proposed", {"version": version, "source": source, "plan": plan, "injected_fault": fault})
        self._emit_decision("plan", None, version, verdict, fault)

    # -------------------------------------------------
    # DAG EXECUTION
    # -------------------------------------------------
    def _execute(self, graph: TaskGraph) -> dict[int, dict]:
        self._plan_faults(graph)
        results: dict[int, dict] = {}
        started: set[int] = set()

        with ThreadPoolExecutor(max_workers=settings.STEP_PARALLELISM, thread_name_prefix="step") as pool:
            running = {}
            try:
                while len(results) < len(graph.steps):
                    for sid in graph.ready(set(results), started):
                        started.add(sid)
                        step = graph.steps[sid]
                        context = [results[d] for d in step.depends_on]
                        running[pool.submit(self._run_step, step, context)] = sid

                    if not running:
                        raise RuntimeError("Scheduler stalled: no runnable steps")

                    finished, _ = wait(running, return_when=FIRST_COMPLETED)
                    for future in finished:
                        sid = running.pop(future)
                        results[sid] = future.result()  # re-raises Aborted / Cancelled
            except BaseException:
                # Stop siblings at their next checkpoint and report never-started steps
                self.halted.set()
                wait(running)
                for sid in graph.order:
                    if sid not in started:
                        self._emit("step.skipped", {"step_id": sid})
                raise

        return results

    def _run_step(self, step: PlanStep, context: list[dict]) -> dict:
        agent = EXECUTION_AGENTS[step.agent]
        step_d = step.model_dump()
        log = get_logger(str(self.execution_id), step.agent)
        feedback = None

        for attempt in range(1, settings.MAX_STEP_RETRIES + 2):
            self._check_cancel()
            self._emit("step.started", {"step_id": step.step_id, "agent": step.agent,
                                        "title": step.title, "attempt": attempt})
            log.info("Step %s attempt %s", step.step_id, attempt)

            t0 = time.perf_counter()
            try:
                resp = agent.run(self.objective, step_d, context, feedback, attempt)
                output, tokens, error = resp.data, resp.tokens, None
            except LLMError as e:
                output, tokens, error = {}, 0, str(e)
            latency_ms = int((time.perf_counter() - t0) * 1000)

            fault = self._fault_for(step.step_id, attempt)
            if fault:
                output = corrupt_output(output, fault)

            self._check_cancel()
            verdict = self.supervisor.review_step(self.objective, step_d, output, attempt)
            tokens += verdict.tokens
            self._add(tokens=tokens)

            status = "completed" if verdict.decision == APPROVE else "rejected"
            self._save(
                AgentExecution(execution_id=self.execution_id, step_id=step.step_id, agent_name=step.agent,
                               attempt=attempt, status=status, objective=step.objective,
                               input_payload={"depends_on": step.depends_on, "feedback": feedback,
                                              "injected_fault": fault},
                               output_payload=output, error=error, latency_ms=latency_ms, tokens=tokens,
                               created_at=datetime.utcnow()),
                SupervisorDecision(execution_id=self.execution_id, target="step", step_id=step.step_id,
                                   attempt=attempt, decision=verdict.decision, reason=verdict.reason,
                                   score=verdict.score,
                                   decision_metadata={"checks": verdict.checks, "feedback": verdict.feedback,
                                                      "injected_fault": fault, "llm_error": error},
                                   created_at=datetime.utcnow()),
            )
            self._emit("step.output", {"step_id": step.step_id, "agent": step.agent, "attempt": attempt,
                                       "output": output, "latency_ms": latency_ms, "tokens": tokens,
                                       "injected_fault": fault, "llm_error": error})
            self._emit_decision("step", step.step_id, attempt, verdict, fault)

            if verdict.decision == APPROVE:
                result = {"step_id": step.step_id, "agent": step.agent, "title": step.title,
                          "status": "completed", "attempts": attempt, "output": output}
                remember(str(self.execution_id), {k: result[k] for k in ("step_id", "agent", "title", "attempts")})
                self._emit("step.completed", {"step_id": step.step_id, "attempts": attempt,
                                              "score": verdict.score})
                return result

            if verdict.decision == ABORT:
                self._emit("step.failed", {"step_id": step.step_id, "reason": verdict.reason})
                raise ExecutionAborted(f"Step {step.step_id} ({step.title}) rejected: {verdict.reason}")

            self._add(retries=1)
            feedback = verdict.feedback

        raise ExecutionAborted(f"Step {step.step_id} exhausted retries")  # unreachable safeguard

    # -------------------------------------------------
    # REPORT
    # -------------------------------------------------
    def _report(self, graph: TaskGraph, results: dict[int, dict]) -> dict:
        self._check_cancel()
        self._emit("agent.started", {"agent": "reporter"})
        steps = [results[sid] for sid in graph.order]
        try:
            resp = ReporterAgent().run(self.objective, steps)
            self._add(tokens=resp.tokens)
            report = FinalReport.model_validate(resp.data).model_dump()
        except Exception as e:
            self.log.warning("Reporter failed (%s) - composing report from step results", e)
            report = {
                "title": self.objective[:80],
                "executive_summary": f"All {len(steps)} steps were approved by the Supervisor.",
                "key_outcomes": [f"{s['title']}: {s['output'].get('summary', 'done')}" for s in steps],
                "next_steps": [],
            }
        report["memory"] = recall(str(self.execution_id))
        self._emit("report.ready", {"report": report})
        return report

    # -------------------------------------------------
    # CHAOS ENGINEERING
    # -------------------------------------------------
    def _plan_faults(self, graph: TaskGraph):
        ids = list(graph.order)
        if self.chaos == "retry":
            for sid in self.rng.sample(ids, k=min(2, len(ids))):
                self.faults[sid] = self.rng.choice(["schema", "hallucination"])
        elif self.chaos == "abort":
            code_steps = [sid for sid in ids if graph.steps[sid].agent == "code"] or ids
            self.faults[self.rng.choice(code_steps)] = "persistent"

    def _fault_for(self, step_id: int, attempt: int) -> str | None:
        kind = self.faults.get(step_id)
        if kind == "persistent":
            return "hallucination" if attempt % 2 else "schema"
        return kind if kind and attempt == 1 else None

    @staticmethod
    def _corrupt_plan(plan: dict) -> dict:
        steps = [dict(s) for s in plan["steps"]]
        if len(steps) >= 2:
            first, last = steps[0], steps[-1]
            first["depends_on"] = list(first.get("depends_on") or []) + [last.get("step_id")]
        return {**plan, "steps": steps}

    # -------------------------------------------------
    # PLUMBING
    # -------------------------------------------------
    def _check_cancel(self):
        if self.cancelled.is_set():
            raise ExecutionCancelled()
        if self.halted.is_set():
            raise ExecutionAborted("Halted because a sibling step was aborted")

    def _emit(self, type_: str, payload: dict):
        bus.publish(self.execution_id, type_, payload)

    def _emit_decision(self, target, step_id, attempt, verdict: Verdict, fault):
        self._emit("supervisor.decision", {
            "target": target, "step_id": step_id, "attempt": attempt, "decision": verdict.decision,
            "score": verdict.score, "reason": verdict.reason, "feedback": verdict.feedback,
            "checks": verdict.checks, "injected_fault": fault,
        })

    def _add(self, tokens: int = 0, retries: int = 0):
        with self._stats_lock:
            self.tokens += tokens
            self.retries += retries

    def _stats(self, started: float) -> dict:
        return {"duration_ms": int((time.perf_counter() - started) * 1000),
                "total_tokens": self.tokens, "retries": self.retries}

    def _save(self, *rows):
        db = SessionLocal()
        try:
            db.add_all(rows)
            db.commit()
        finally:
            db.close()

    def _update(self, **fields):
        db = SessionLocal()
        try:
            run = db.get(ExecutionRun, self.execution_id)
            for k, v in fields.items():
                setattr(run, k, v)
            run.updated_at = datetime.utcnow()
            db.commit()
        finally:
            db.close()

    def _finish(self, status: str, started: float, result: dict | None = None, error: str | None = None):
        stats = self._stats(started)
        self._update(status=status, phase=None, result=result, error=error, finished_at=datetime.utcnow(),
                     duration_ms=stats["duration_ms"], total_tokens=stats["total_tokens"], retries=stats["retries"])


def llm_source() -> str:
    return "llm" if get_llm().mode == "live" else "simulated"


def fallback_plan(objective: str) -> dict:
    """Deterministic 3-step plan used when the planner can't produce a valid one."""
    return {
        "summary": "Fallback plan: research, implement, then execute.",
        "steps": [
            {"step_id": 1, "agent": "research", "title": "Analyse requirements",
             "objective": f"Analyse the requirements and constraints of: {objective}",
             "depends_on": [], "expected_output": "Requirements and risks"},
            {"step_id": 2, "agent": "code", "title": "Implement core solution",
             "objective": f"Implement the core logic needed for: {objective}",
             "depends_on": [1], "expected_output": "Working code with tests"},
            {"step_id": 3, "agent": "automation", "title": "Execute workflow",
             "objective": f"Run the implemented workflow end to end for: {objective}",
             "depends_on": [2], "expected_output": "Executed actions and outcome"},
        ],
    }


def corrupt_output(output: dict, kind: str) -> dict:
    """Simulate the two classic LLM failure modes the Supervisor must catch."""
    output = dict(output)
    if kind == "schema":
        for key in ("findings", "files", "actions"):
            output.pop(key, None)
    else:
        output["summary"] = HALLUCINATION
    return output
