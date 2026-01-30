from pydantic import BaseModel
from typing import Any, List
from uuid import UUID


class StartExecutionRequest(BaseModel):
    user_objective: str


class ExecutionResponse(BaseModel):
    execution_id: UUID
    status: str


class AgentExecutionResponse(BaseModel):
    step_id: int
    agent_name: str
    output_payload: Any
    status: str
