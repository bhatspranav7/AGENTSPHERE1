"""Agents turn a step into structured output via the LLM layer.

They are deliberately thin: prompting and context assembly only. Validation,
retries and persistence belong to the Supervisor and Orchestrator.
"""
import json
from dataclasses import dataclass
from typing import Any

from ..core import prompts
from ..core.config import settings
from ..llm import LLMResponse, get_llm


def _clip(value: Any, limit: int = 1800) -> str:
    text = json.dumps(value, default=str, ensure_ascii=False)
    return text if len(text) <= limit else text[:limit] + "…"


@dataclass(frozen=True)
class AgentInfo:
    name: str
    role: str
    description: str
    color: str


class BaseExecutionAgent:
    info: AgentInfo
    system_prompt: str

    def run(self, objective: str, step: dict, context: list[dict], feedback: str | None, attempt: int) -> LLMResponse:
        user = [
            f"Overall objective: {objective}",
            f"Your step ({step['step_id']}): {step['title']}",
            f"Step objective: {step['objective']}",
            f"Expected output: {step['expected_output']}",
        ]
        if context:
            user.append("Outputs of the steps you depend on:\n" + "\n".join(
                f"- step {c['step_id']} ({c['agent']}): {_clip(c['output'])}" for c in context
            ))
        if feedback:
            user.append(f"Your previous attempt was rejected by the Supervisor. Fix this: {feedback}")

        return get_llm().complete_json(
            task=self.info.name,
            system=self.system_prompt,
            user="\n\n".join(user),
            sim={"objective": objective, "step": step, "step_id": step["step_id"], "attempt": attempt},
        )


class ResearchAgent(BaseExecutionAgent):
    info = AgentInfo("research", "Analyst", "Requirements, domain constraints, risks and recommendations.", "#7aa8ff")
    system_prompt = prompts.RESEARCH_SYSTEM_PROMPT


class CodeAgent(BaseExecutionAgent):
    info = AgentInfo("code", "Engineer", "Writes runnable source code and tests for the plan.", "#b58cff")
    system_prompt = prompts.CODE_SYSTEM_PROMPT


class AutomationAgent(BaseExecutionAgent):
    info = AgentInfo("automation", "Operator", "Executes integrations and workflow actions in a sandbox.", "#f2c14e")
    system_prompt = prompts.AUTOMATION_SYSTEM_PROMPT


class PlannerAgent:
    info = AgentInfo("planner", "Strategist", "Decomposes the objective into a dependency graph of agent tasks.", "#67d4ea")

    def run(self, objective: str, feedback: str | None, attempt: int) -> LLMResponse:
        user = f"Objective: {objective}"
        if feedback:
            user += f"\n\nYour previous plan was rejected by the Supervisor. Fix these problems: {feedback}"
        return get_llm().complete_json(
            task="plan",
            system=prompts.PLANNER_SYSTEM_PROMPT.format(max_steps=settings.MAX_PLAN_STEPS),
            user=user,
            sim={"objective": objective, "attempt": attempt},
        )


class ReporterAgent:
    info = AgentInfo("reporter", "Narrator", "Summarises the finished run for stakeholders.", "#6fd49b")

    def run(self, objective: str, steps: list[dict]) -> LLMResponse:
        return get_llm().complete_json(
            task="report",
            system=prompts.REPORTER_SYSTEM_PROMPT,
            user=f"Objective: {objective}\n\nStep results:\n" + "\n".join(
                f"- {s['title']} ({s['agent']}, {s['status']}): {_clip(s.get('output'), 700)}" for s in steps
            ),
            sim={"objective": objective, "steps": steps},
        )


EXECUTION_AGENTS: dict[str, BaseExecutionAgent] = {
    "research": ResearchAgent(),
    "code": CodeAgent(),
    "automation": AutomationAgent(),
}

SUPERVISOR_INFO = AgentInfo(
    "supervisor", "Guardian", "Validates every plan and output; decides APPROVE, RETRY or ABORT.", "#f07878"
)

REGISTRY: list[AgentInfo] = [
    PlannerAgent.info,
    ResearchAgent.info,
    CodeAgent.info,
    AutomationAgent.info,
    SUPERVISOR_INFO,
    ReporterAgent.info,
]
