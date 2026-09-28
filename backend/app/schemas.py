"""Contracts between agents. The Supervisor validates every LLM output
against these before anything downstream is allowed to consume it."""
from typing import Literal

from pydantic import BaseModel, Field, field_validator

AgentName = Literal["research", "code", "automation"]


# -------------------------------------------------
# PLANNER
# -------------------------------------------------
class PlanStep(BaseModel):
    step_id: int = Field(ge=1)
    agent: AgentName
    title: str = Field(min_length=3, max_length=80)
    objective: str = Field(min_length=10, max_length=600)
    depends_on: list[int] = Field(default_factory=list)
    expected_output: str = Field(min_length=5, max_length=300)

    @field_validator("agent", mode="before")
    @classmethod
    def normalize_agent(cls, v):
        # LLMs often answer "ResearchAgent" or "Research"
        if isinstance(v, str):
            v = v.strip().lower().removesuffix("agent").strip()
        return v


class ExecutionPlanSchema(BaseModel):
    summary: str = Field(min_length=10, max_length=400)
    steps: list[PlanStep] = Field(min_length=1)


# -------------------------------------------------
# EXECUTION AGENTS
# -------------------------------------------------
class ResearchOutput(BaseModel):
    summary: str = Field(min_length=30)
    findings: list[str] = Field(min_length=2)
    risks: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(min_length=1)


class CodeFile(BaseModel):
    path: str = Field(min_length=3)
    content: str = Field(min_length=40)


class CodeOutput(BaseModel):
    summary: str = Field(min_length=30)
    language: str = Field(min_length=2)
    files: list[CodeFile] = Field(min_length=1)
    how_to_run: str | None = None


class AutomationAction(BaseModel):
    name: str = Field(min_length=3)
    system: str = Field(min_length=2)
    status: Literal["success", "skipped", "failed"]
    detail: str = Field(min_length=5)


class AutomationOutput(BaseModel):
    summary: str = Field(min_length=30)
    actions: list[AutomationAction] = Field(min_length=1)
    outcome: str = Field(min_length=10)


OUTPUT_SCHEMAS: dict[str, type[BaseModel]] = {
    "research": ResearchOutput,
    "code": CodeOutput,
    "automation": AutomationOutput,
}


# -------------------------------------------------
# SUPERVISOR / REPORT
# -------------------------------------------------
class ReviewVerdict(BaseModel):
    score: float = Field(ge=0, le=1)
    approved: bool
    reason: str = Field(min_length=3)
    feedback: str | None = None


class FinalReport(BaseModel):
    title: str = Field(min_length=3)
    executive_summary: str = Field(min_length=30)
    key_outcomes: list[str] = Field(min_length=1)
    next_steps: list[str] = Field(default_factory=list)


# -------------------------------------------------
# API
# -------------------------------------------------
ChaosMode = Literal["off", "retry", "abort"]


class StartExecutionRequest(BaseModel):
    user_objective: str = Field(min_length=5, max_length=500)
    chaos: ChaosMode = "off"
