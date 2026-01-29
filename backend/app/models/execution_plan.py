from pydantic import BaseModel, Field
from typing import List, Literal


AgentType = Literal["research", "code", "automation", "supervisor"]


class PlanStep(BaseModel):
    step_id: int = Field(..., description="Sequential step number")
    agent: AgentType = Field(..., description="Agent responsible for this step")
    objective: str = Field(..., description="Goal of this step")
    inputs: List[str] = Field(default_factory=list)
    expected_output: str


class ExecutionPlan(BaseModel):
    user_objective: str
    steps: List[PlanStep]
