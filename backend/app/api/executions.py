from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend.app.db.session import get_db
from backend.app.services.execution_service import ExecutionService
from backend.app.core.security import verify_api_key
from backend.app.core.exceptions import ExecutionError, execution_http_error
from backend.app.core.logging import get_logger

router = APIRouter(
    prefix="/executions",
    dependencies=[Depends(verify_api_key)],
)


@router.post("/start")
def start_execution(payload: dict, db: Session = Depends(get_db)):
    logger = get_logger()
    logger.info("Received execution start request")

    try:
        service = ExecutionService(db)
        execution_id = service.start_execution(payload["user_objective"])

        return {
            "execution_id": execution_id,
            "status": "completed",
        }

    except ExecutionError:
        raise execution_http_error("Execution failed")

    except Exception:
        raise execution_http_error("Unexpected server error")


@router.get("/{execution_id}")
def get_execution_status(execution_id: str, db: Session = Depends(get_db)):
    service = ExecutionService(db)
    run = service.get_execution_status(execution_id)

    if not run:
        return {"error": "Execution not found"}

    return {
        "execution_id": str(run.execution_id),
        "status": run.status,
    }


@router.get("")
def list_executions(
    limit: int = Query(default=10, le=50),
    db: Session = Depends(get_db),
):
    service = ExecutionService(db)
    runs = service.list_executions(limit=limit)

    return [
        {
            "execution_id": str(run.execution_id),
            "status": run.status,
            "created_at": run.created_at,
        }
        for run in runs
    ]
