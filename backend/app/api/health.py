from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text

from backend.app.db.session import get_db

router = APIRouter(prefix="/health")


@router.get("")
def health_check(db: Session = Depends(get_db)):
    """
    Health check endpoint.
    Verifies API is running and database is reachable.
    """
    try:
        db.execute(text("SELECT 1"))
        return {
            "status": "ok",
            "database": "reachable",
        }
    except Exception:
        return {
            "status": "degraded",
            "database": "unreachable",
        }
