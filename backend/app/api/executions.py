from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.app.db.session import get_db
from backend.app.services.execution_service import ExecutionService
from backend.app.core.security import verify_api_key
from backend.app.core.exceptions import ExecutionError, execution_http_error

router = APIRouter(
    prefix="/executions",
    dependencies=[Depends(verify_api_key)],
)


@router.post("/start")
def start_execution(payload: dict, db: Session = Depends(get_db)):
    try:
        service = ExecutionService(db)
        execution_id = service.start_execution(
            payload["user_objective"]
        )

        return {
            "execution_id": execution_id,
            "status": "completed",
        }

    except ExecutionError:
        raise execution_http_error("Execution failed")

    except Exception:
        raise execution_http_error("Unexpected server error")
