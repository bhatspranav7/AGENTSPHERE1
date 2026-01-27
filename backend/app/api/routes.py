from fastapi import APIRouter
from app.agents.planner_agent import PlannerAgent
from app.workflows.orchestrator import Orchestrator

router = APIRouter()


@router.post("/workflows/execute")
def execute_workflow(request: dict):
    user_request = request.get("request")

    planner = PlannerAgent()
    orchestrator = Orchestrator()

    task_graph = planner.plan(workflow_id=1, user_request=user_request)
    orchestrator.execute(task_graph)

    return {
        "message": "Workflow executed successfully",
        "tasks": task_graph.tasks
    }
