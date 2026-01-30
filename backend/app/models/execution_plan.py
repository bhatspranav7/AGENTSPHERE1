from typing import List
from pydantic import BaseModel, Field


class PlanStepSchema(BaseModel):
    step_id: int = Field(..., example=1)
    agent: str = Field(..., example="research")
    objective: str = Field(..., example="Analyze requirements")
    inputs: List[str] = Field(default_factory=list)
    expected_output: str = Field(..., example="Clear understanding")


class ExecutionPlanSchema(BaseModel):
    user_objective: str
    steps: List[PlanStepSchema]
