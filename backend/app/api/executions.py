from fastapi import APIRouter, HTTPException
from uuid import UUID

from backend.app.api.schemas import (
    StartExecutionRequest,
    ExecutionResponse,
    AgentExecutionResponse,
)
from backend.app.agents.planner_agent import PlannerAgent
from backend.app.services.execution_engine import ExecutionEngine
from backend.app.db.session import SessionLocal
from backend.app.models.execution import ExecutionRun, ExecutionPlan
from backend.app.models.agent_execution import AgentExecution

router = APIRouter(prefix="/executions", tags=["Executions"])


@router.post("/start", response_model=ExecutionResponse)
def start_execution(payload: StartExecutionRequest):
    planner = PlannerAgent()
    engine = ExecutionEngine()

    execution_id, plan = planner.create_plan(payload.user_objective)
    engine.run(execution_id, plan)

    return ExecutionResponse(
        execution_id=execution_id,
        status="completed",
    )


@router.get("/{execution_id}", response_model=ExecutionResponse)
def get_execution(execution_id: UUID):
    db = SessionLocal()
    run = db.query(ExecutionRun).filter(
        ExecutionRun.execution_id == execution_id
    ).first()

    if not run:
        raise HTTPException(status_code=404, detail="Execution not found")

    return ExecutionResponse(
        execution_id=run.execution_id,
        status=run.status,
    )


@router.get("/{execution_id}/plans")
def get_execution_plans(execution_id: UUID):
    db = SessionLocal()
    plans = (
        db.query(ExecutionPlan)
        .filter(ExecutionPlan.execution_id == execution_id)
        .order_by(ExecutionPlan.version)
        .all()
    )

    return [
        {
            "version": p.version,
            "plan": p.plan_json,
            "validation_errors": p.validation_errors,
            "created_at": p.created_at,
        }
        for p in plans
    ]


@router.get("/{execution_id}/agents", response_model=list[AgentExecutionResponse])
def get_agent_executions(execution_id: UUID):
    db = SessionLocal()
    records = (
        db.query(AgentExecution)
        .filter(AgentExecution.execution_id == execution_id)
        .order_by(AgentExecution.step_id)
        .all()
    )

    return [
        AgentExecutionResponse(
            step_id=r.step_id,
            agent_name=r.agent_name,
            output_payload=r.output_payload,
            status=r.status,
        )
        for r in records
    ]
