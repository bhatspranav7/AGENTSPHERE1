from app.workflows.task_graph import TaskGraph
from app.models.agent_log import AgentLog
from app.db.session import SessionLocal


class Orchestrator:
    """
    Orchestrator controls execution of a TaskGraph.
    """

    def execute(self, task_graph: TaskGraph):
        db = SessionLocal()

        for task in task_graph.tasks:
            log = AgentLog(
                agent_name=task.agent,
                action=task.action,
                status="EXECUTED"
            )
            db.add(log)

            task.status = "COMPLETED"

        db.commit()
        db.close()
