from datetime import datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import case, func, text
from sqlalchemy.orm import Session

from ..agents import REGISTRY
from ..core.cache import CACHE_MODE, cache
from ..core.config import settings
from ..core.security import Principal, verify_api_key
from ..db.session import get_db
from ..llm import get_llm
from ..models import AgentExecution, ExecutionRun, ExecutionStatus, SupervisorDecision
from ..services.runner import runner

router = APIRouter(tags=["System"])


@router.get("/health")
def health_check(db: Session = Depends(get_db)):
    """
    Health check endpoint.
    Verifies API is running and database / cache are reachable.
    """
    try:
        db.execute(text("SELECT 1"))
        database = "reachable"
    except Exception:
        database = "unreachable"

    try:
        cache.ping()
        cache_state = CACHE_MODE
    except Exception:
        cache_state = "unreachable"

    llm = get_llm()
    return {
        "status": "ok" if database == "reachable" else "degraded",
        "database": database,
        "cache": cache_state,
        "llm_mode": llm.mode,
        "llm_model": llm.model,
        "active_executions": runner.active_count(),
    }


@router.get("/config/public")
def public_config():
    """What the UI needs before the user has a key. Never exposes admin keys."""
    llm = get_llm()
    return {
        "demo_api_key": settings.DEMO_API_KEY or None,
        "demo_rate_limit_per_hour": settings.DEMO_RATE_LIMIT_PER_HOUR,
        "llm_mode": llm.mode,
        "llm_model": llm.model,
        "max_step_retries": settings.MAX_STEP_RETRIES,
        "max_plan_retries": settings.MAX_PLAN_RETRIES,
        "step_parallelism": settings.STEP_PARALLELISM,
    }


@router.get("/agents")
def list_agents(db: Session = Depends(get_db), _: Principal = Depends(verify_api_key)):
    stats = {
        row.agent_name: row
        for row in db.query(
            AgentExecution.agent_name,
            func.count(AgentExecution.id).label("attempts"),
            func.sum(case((AgentExecution.status == "completed", 1), else_=0)).label("approved"),
            func.avg(AgentExecution.latency_ms).label("avg_latency"),
            func.sum(AgentExecution.tokens).label("tokens"),
        ).group_by(AgentExecution.agent_name)
    }
    result = []
    for info in REGISTRY:
        row = stats.get(info.name)
        attempts = row.attempts if row else 0
        approved = int(row.approved or 0) if row else 0
        result.append({
            "name": info.name, "role": info.role, "description": info.description, "color": info.color,
            "attempts": attempts,
            "approval_rate": round(approved / attempts, 3) if attempts else None,
            "avg_latency_ms": int(row.avg_latency) if row and row.avg_latency else None,
            "tokens": int(row.tokens or 0) if row else 0,
        })
    return result


@router.get("/metrics")
def metrics(db: Session = Depends(get_db), _: Principal = Depends(verify_api_key)):
    by_status = dict(db.query(ExecutionRun.status, func.count()).group_by(ExecutionRun.status).all())
    terminal = sum(by_status.get(s, 0) for s in ExecutionStatus.TERMINAL)

    completed = db.query(
        func.avg(ExecutionRun.duration_ms), func.sum(ExecutionRun.total_tokens), func.sum(ExecutionRun.retries)
    ).filter(ExecutionRun.status == ExecutionStatus.COMPLETED).one()

    durations = [d for (d,) in db.query(ExecutionRun.duration_ms)
                 .filter(ExecutionRun.status == ExecutionStatus.COMPLETED, ExecutionRun.duration_ms.isnot(None))
                 .order_by(ExecutionRun.created_at.desc()).limit(200)]
    p95 = sorted(durations)[int(len(durations) * 0.95) - 1] if len(durations) >= 2 else (durations[0] if durations else None)

    decisions = dict(db.query(SupervisorDecision.decision, func.count()).group_by(SupervisorDecision.decision).all())

    since = datetime.utcnow() - timedelta(days=13)
    day = func.date(ExecutionRun.created_at)
    daily_rows = (db.query(day, ExecutionRun.status, func.count())
                  .filter(ExecutionRun.created_at >= since.replace(hour=0, minute=0, second=0, microsecond=0))
                  .group_by(day, ExecutionRun.status).all())
    daily: dict[str, dict[str, int]] = {}
    for i in range(14):
        daily[(since + timedelta(days=i)).date().isoformat()] = {}
    for d, status, count in daily_rows:
        daily.setdefault(str(d), {})[status] = count

    return {
        "total_executions": sum(by_status.values()),
        "by_status": by_status,
        "success_rate": round(by_status.get(ExecutionStatus.COMPLETED, 0) / terminal, 3) if terminal else None,
        "avg_duration_ms": int(completed[0]) if completed[0] else None,
        "p95_duration_ms": p95,
        "total_tokens": int(completed[1] or 0),
        "total_retries": int(completed[2] or 0),
        "supervisor_decisions": decisions,
        "daily": [{"date": d, **counts} for d, counts in daily.items()],
        "active_executions": runner.active_count(),
    }
