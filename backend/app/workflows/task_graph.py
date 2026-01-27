from typing import List, Dict
from pydantic import BaseModel


class Task(BaseModel):
    task_id: str
    agent: str
    action: str
    input: Dict
    status: str = "PENDING"


class TaskGraph(BaseModel):
    workflow_id: int
    tasks: List[Task]

    def get_pending_tasks(self) -> List[Task]:
        return [task for task in self.tasks if task.status == "PENDING"]
