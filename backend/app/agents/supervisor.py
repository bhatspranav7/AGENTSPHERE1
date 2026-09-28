"""Supervisor: the control layer.

The LLM proposes, the Supervisor disposes. Every plan and every agent output
passes through here; nothing reaches a downstream agent without an APPROVE.
Checks are deterministic first (schema, graph, heuristics) so they work without
an LLM; a live LLM additionally acts as a judge.
"""
import json
import logging
import re
from dataclasses import dataclass, field

from pydantic import ValidationError

from ..core import prompts
from ..core.config import settings
from ..llm import get_llm
from ..orchestrator.task_graph import GraphError, TaskGraph
from ..schemas import OUTPUT_SCHEMAS, ExecutionPlanSchema, ReviewVerdict

logger = logging.getLogger(__name__)

APPROVE, RETRY, ABORT = "APPROVE", "RETRY", "ABORT"
PASS_SCORE = 0.6

_REFUSAL = re.compile(
    r"as an ai( language model)?|i (cannot|can't|am unable to)|lorem ipsum|\bplaceholder\b|\btodo\b|insert .* here",
    re.IGNORECASE,
)
_STOPWORDS = set("""a an and are as at be by for from has in into is it its of on or that the this to was
were will with your their our you we they them should must can using use via per each all any""".split())


@dataclass
class Verdict:
    decision: str
    score: float
    reason: str
    feedback: str | None = None
    checks: list[dict] = field(default_factory=list)
    tokens: int = 0


def _format_errors(e: ValidationError) -> list[str]:
    return [f"{'.'.join(str(p) for p in err['loc']) or 'root'}: {err['msg']}" for err in e.errors()[:6]]


def _keywords(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z][a-z0-9-]{3,}", text.lower()) if w not in _STOPWORDS}


class SupervisorAgent:
    """
    Validates planner output, enforces schema,
    retries on failure, logs all decisions.
    """

    # -------------------------------------------------
    # PLAN REVIEW
    # -------------------------------------------------
    def review_plan(self, plan: dict, attempt: int) -> tuple[Verdict, ExecutionPlanSchema | None, TaskGraph | None]:
        checks = []
        try:
            validated = ExecutionPlanSchema.model_validate(plan)
            checks.append({"name": "schema", "passed": True})
        except ValidationError as e:
            errors = _format_errors(e)
            checks.append({"name": "schema", "passed": False, "detail": errors})
            return self._retry_or_abort(attempt, settings.MAX_PLAN_RETRIES, 0.0,
                                        "Plan does not match the schema", "; ".join(errors), checks), None, None

        if len(validated.steps) > settings.MAX_PLAN_STEPS:
            checks.append({"name": "size", "passed": False})
            return self._retry_or_abort(attempt, settings.MAX_PLAN_RETRIES, 0.3,
                                        f"Plan has {len(validated.steps)} steps",
                                        f"Use at most {settings.MAX_PLAN_STEPS} steps.", checks), None, None
        checks.append({"name": "size", "passed": True, "detail": len(validated.steps)})

        try:
            graph = TaskGraph.from_steps(validated.steps)
            checks.append({"name": "dag", "passed": True, "detail": f"depth {max(graph.levels.values()) + 1}"})
        except GraphError as e:
            checks.append({"name": "dag", "passed": False, "detail": str(e)})
            return self._retry_or_abort(attempt, settings.MAX_PLAN_RETRIES, 0.2,
                                        f"Invalid dependency graph: {e}",
                                        f"{e}. depends_on may only reference earlier steps.", checks), None, None

        return Verdict(APPROVE, 1.0, "Plan is well-formed and acyclic", checks=checks), validated, graph

    # -------------------------------------------------
    # STEP REVIEW
    # -------------------------------------------------
    def review_step(self, objective: str, step: dict, output: dict, attempt: int) -> Verdict:
        checks: list[dict] = []
        schema = OUTPUT_SCHEMAS[step["agent"]]

        try:
            validated = schema.model_validate(output)
            checks.append({"name": "schema", "passed": True})
        except ValidationError as e:
            errors = _format_errors(e)
            checks.append({"name": "schema", "passed": False, "detail": errors})
            return self._retry_or_abort(attempt, settings.MAX_STEP_RETRIES, 0.0,
                                        "Output does not match the agent contract",
                                        "Return every required field: " + "; ".join(errors), checks)

        text = json.dumps(validated.model_dump(), ensure_ascii=False)

        refusal = _REFUSAL.search(text)
        checks.append({"name": "no_hallucination_markers", "passed": refusal is None,
                       **({"detail": refusal.group(0)} if refusal else {})})

        wanted = _keywords(objective + " " + step["objective"])
        overlap = len(wanted & _keywords(text)) / max(len(wanted), 1)
        checks.append({"name": "relevance", "passed": overlap >= 0.15, "detail": round(overlap, 2)})

        if step["agent"] == "code":
            has_code = any(re.search(r"\b(def|class|function|const|import|fn)\b", f["content"]) for f in output["files"])
            checks.append({"name": "contains_code", "passed": has_code})
        if step["agent"] == "automation":
            ok = any(a["status"] == "success" for a in output["actions"])
            checks.append({"name": "actions_executed", "passed": ok})

        heuristic = sum(c["passed"] for c in checks) / len(checks)
        score, reason, feedback, tokens = heuristic, None, None, 0

        failed = [c["name"] for c in checks if not c["passed"]]
        if failed:
            reason = f"Failed checks: {', '.join(failed)}"
            feedback = self._feedback_for(failed, step)
        elif get_llm().mode == "live":
            judged = self._judge(objective, step, validated.model_dump())
            if judged is not None:
                verdict, tokens = judged
                score = round(0.4 * heuristic + 0.6 * verdict.score, 3)
                reason = verdict.reason
                feedback = verdict.feedback if not verdict.approved else None
                checks.append({"name": "llm_judge", "passed": verdict.approved, "detail": verdict.score})
        else:
            # Simulated mode: deterministic heuristics only, reported honestly
            reason = "All deterministic checks passed"

        score = round(score, 3)
        if score >= PASS_SCORE and all(c["passed"] for c in checks):
            return Verdict(APPROVE, score, reason or "Output meets the step objective", checks=checks, tokens=tokens)

        verdict = self._retry_or_abort(attempt, settings.MAX_STEP_RETRIES, score,
                                       reason or "Quality below threshold", feedback, checks)
        verdict.tokens = tokens
        return verdict

    # -------------------------------------------------
    # HELPERS
    # -------------------------------------------------
    @staticmethod
    def _retry_or_abort(attempt, max_retries, score, reason, feedback, checks) -> Verdict:
        if attempt <= max_retries:
            return Verdict(RETRY, score, reason, feedback, checks)
        return Verdict(ABORT, score, f"{reason} (retry budget of {max_retries} exhausted)", feedback, checks)

    @staticmethod
    def _feedback_for(failed: list[str], step: dict) -> str:
        hints = {
            "no_hallucination_markers": "Remove refusals, placeholders and TODOs; give concrete content.",
            "relevance": f"Stay on the step objective: {step['objective']}",
            "contains_code": "Files must contain real source code, not prose.",
            "actions_executed": "At least one action must have been executed successfully.",
        }
        return " ".join(hints[f] for f in failed if f in hints)

    def _judge(self, objective, step, output) -> tuple[ReviewVerdict, int] | None:
        try:
            resp = get_llm().complete_json(
                task="review",
                system=prompts.SUPERVISOR_SYSTEM_PROMPT,
                user=(f"Overall objective: {objective}\nStep: {step['title']} ({step['agent']})\n"
                      f"Step objective: {step['objective']}\n\nAgent output:\n"
                      f"{json.dumps(output, ensure_ascii=False)[:6000]}"),
                sim={"objective": objective, "step": step, "step_id": step["step_id"]},
            )
            return ReviewVerdict.model_validate(resp.data), resp.tokens
        except Exception as e:
            # A broken judge must not block the run; heuristics already passed
            logger.warning("LLM judge unavailable: %s", e)
            return None
