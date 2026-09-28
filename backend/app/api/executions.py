import asyncio
import json
import time
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..core.logging import get_logger
from ..core.security import Principal, enforce_rate_limit, verify_api_key
from ..db.session import SessionLocal, get_db
from ..llm import get_llm
from ..models import AgentExecution, ExecutionEvent, ExecutionPlan, ExecutionRun, ExecutionStatus, SupervisorDecision
from ..schemas import StartExecutionRequest
from ..services.events import TERMINAL_EVENTS, bus, serialize
from ..services.runner import runner

router = APIRouter(prefix="/executions", tags=["Executions"])


def _uuid(value: str) -> uuid.UUID:
    try:
        return uuid.UUID(value)
    except ValueError:
        raise HTTPException(status_code=404, detail={"error": "Execution not found"})


def _get_run(db: Session, execution_id: str) -> ExecutionRun:
    run = db.get(ExecutionRun, _uuid(execution_id))
    if not run:
        raise HTTPException(status_code=404, detail={"error": "Execution not found"})
    return run


def _iso(dt: datetime | None) -> str | None:
    return dt.isoformat() + "Z" if dt else None


def serialize_run(run: ExecutionRun) -> dict:
    return {
        "execution_id": str(run.execution_id),
        "objective": run.objective,
        "status": run.status,
        "phase": run.phase,
        "llm_mode": run.llm_mode,
        "llm_model": run.llm_model,
        "chaos": run.chaos_mode or ("retry" if run.chaos else "off"),
        "parent_id": str(run.parent_id) if run.parent_id else None,
        "error": run.error,
        "total_tokens": run.total_tokens or 0,
        "retries": run.retries or 0,
        "duration_ms": run.duration_ms,
        "created_at": _iso(run.created_at),
        "started_at": _iso(run.started_at),
        "finished_at": _iso(run.finished_at),
    }


def _launch(db: Session, objective: str, chaos: str, parent_id: uuid.UUID | None = None) -> ExecutionRun:
    llm = get_llm()
    run = ExecutionRun(
        execution_id=uuid.uuid4(),
        objective=objective.strip(),
        status=ExecutionStatus.QUEUED,
        chaos=chaos != "off",
        llm_mode=llm.mode,
        llm_model=llm.model,
        chaos_mode=chaos,
        parent_id=parent_id,
        created_at=datetime.utcnow(),
    )
    db.add(run)
    db.commit()
    bus.publish(run.execution_id, "execution.queued", {"objective": run.objective, "chaos": chaos})
    runner.submit(run.execution_id, run.objective, chaos)
    get_logger(str(run.execution_id)).info("Execution queued")
    return run


def _wait_until_done(execution_id: uuid.UUID, timeout: float = 300) -> ExecutionRun:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        db = SessionLocal()
        try:
            run = db.get(ExecutionRun, execution_id)
            if run.status in ExecutionStatus.TERMINAL:
                return run
        finally:
            db.close()
        time.sleep(0.5)
    raise HTTPException(status_code=504, detail={"error": "Execution still running", "execution_id": str(execution_id)})


# -------------------------------------------------
# START
# -------------------------------------------------
@router.post("", status_code=202)
def create_execution(
    payload: StartExecutionRequest,
    db: Session = Depends(get_db),
    _: Principal = Depends(enforce_rate_limit),
):
    """Queue an execution and return immediately. Follow it via `/stream`."""
    return serialize_run(_launch(db, payload.user_objective, payload.chaos))


@router.post("/start")
def start_execution(
    payload: StartExecutionRequest,
    wait: bool = Query(default=True, description="Block until the run finishes (v1 behaviour)"),
    db: Session = Depends(get_db),
    _: Principal = Depends(enforce_rate_limit),
):
    """Backward-compatible v1 endpoint: runs the workflow and returns its final status."""
    run = _launch(db, payload.user_objective, payload.chaos)
    if wait:
        run = _wait_until_done(run.execution_id)
    return {"execution_id": str(run.execution_id), "status": run.status}


@router.post("/{execution_id}/replay", status_code=202)
def replay_execution(
    execution_id: str,
    db: Session = Depends(get_db),
    _: Principal = Depends(enforce_rate_limit),
):
    """Re-run the same objective (with the same chaos setting) as a new execution."""
    original = _get_run(db, execution_id)
    chaos = original.chaos_mode or "off"
    return serialize_run(_launch(db, original.objective or "", chaos, parent_id=original.execution_id))


@router.post("/{execution_id}/cancel")
def cancel_execution(
    execution_id: str,
    db: Session = Depends(get_db),
    _: Principal = Depends(verify_api_key),
):
    run = _get_run(db, execution_id)
    if run.status in ExecutionStatus.TERMINAL:
        raise HTTPException(status_code=409, detail={"error": f"Execution already {run.status}"})
    runner.cancel(execution_id)
    return {"execution_id": execution_id, "status": "cancelling"}


# -------------------------------------------------
# READ
# -------------------------------------------------
@router.get("")
def list_executions(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    status: str | None = Query(default=None),
    q: str | None = Query(default=None, max_length=100),
    db: Session = Depends(get_db),
    _: Principal = Depends(verify_api_key),
):
    query = db.query(ExecutionRun)
    if status:
        query = query.filter(ExecutionRun.status == status)
    if q:
        query = query.filter(ExecutionRun.objective.ilike(f"%{q}%"))
    total = query.count()
    runs = query.order_by(ExecutionRun.created_at.desc()).offset(offset).limit(limit).all()
    return {"total": total, "items": [serialize_run(r) for r in runs]}


@router.get("/{execution_id}")
def get_execution(
    execution_id: str,
    db: Session = Depends(get_db),
    _: Principal = Depends(verify_api_key),
):
    """Full audit record: run, every plan version, every agent attempt, every supervisor verdict."""
    run = _get_run(db, execution_id)
    eid = run.execution_id

    plans = db.query(ExecutionPlan).filter(ExecutionPlan.execution_id == eid).order_by(ExecutionPlan.version).all()
    steps = db.query(AgentExecution).filter(AgentExecution.execution_id == eid).order_by(AgentExecution.id).all()
    decisions = (db.query(SupervisorDecision).filter(SupervisorDecision.execution_id == eid)
                 .order_by(SupervisorDecision.id).all())

    return {
        **serialize_run(run),
        "result": run.result if run.status == ExecutionStatus.COMPLETED else None,
        "plans": [{"version": p.version, "source": p.source, "approved": p.approved,
                   "plan": p.plan_json, "validation_errors": p.validation_errors,
                   "created_at": _iso(p.created_at)} for p in plans],
        "agent_executions": [{"step_id": s.step_id, "agent": s.agent_name, "attempt": s.attempt,
                              "status": s.status, "objective": s.objective, "output": s.output_payload,
                              "input": s.input_payload, "error": s.error, "latency_ms": s.latency_ms,
                              "tokens": s.tokens, "created_at": _iso(s.created_at)} for s in steps],
        "supervisor_decisions": [{"target": d.target, "step_id": d.step_id, "attempt": d.attempt,
                                  "decision": d.decision, "reason": d.reason, "score": d.score,
                                  "metadata": d.decision_metadata, "created_at": _iso(d.created_at)}
                                 for d in decisions],
    }


@router.get("/{execution_id}/events")
def list_events(
    execution_id: str,
    after: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    _: Principal = Depends(verify_api_key),
):
    _get_run(db, execution_id)
    rows = (db.query(ExecutionEvent)
            .filter(ExecutionEvent.execution_id == _uuid(execution_id), ExecutionEvent.id > after)
            .order_by(ExecutionEvent.id).all())
    return [serialize(r) for r in rows]


@router.get("/{execution_id}/stream")
async def stream_events(
    execution_id: str,
    request: Request,
    last_event_id: str | None = Header(default=None),
    _: Principal = Depends(verify_api_key),
):
    """Server-Sent Events: replays history from the DB, then tails live events."""
    eid = _uuid(execution_id)
    key = str(eid)
    after = int(last_event_id) if last_event_id and last_event_id.isdigit() else 0

    # Subscribe before reading history so nothing falls in the gap
    queue = bus.subscribe(key)

    def load_history():
        db = SessionLocal()
        try:
            if not db.get(ExecutionRun, eid):
                return None, None
            rows = db.execute(select(ExecutionEvent).where(ExecutionEvent.execution_id == eid,
                                                           ExecutionEvent.id > after)
                              .order_by(ExecutionEvent.id)).scalars().all()
            status = db.get(ExecutionRun, eid).status
            return [serialize(r) for r in rows], status
        finally:
            db.close()

    history, status = await asyncio.to_thread(load_history)
    if history is None:
        bus.unsubscribe(key, queue)
        raise HTTPException(status_code=404, detail={"error": "Execution not found"})

    def frame(event: dict) -> str:
        return f"id: {event['id']}\nevent: {event['type']}\ndata: {json.dumps(event, default=str)}\n\n"

    async def generator():
        seen = after
        try:
            yield "retry: 2000\n\n"
            for event in history:
                seen = event["id"]
                yield frame(event)
                if event["type"] in TERMINAL_EVENTS:
                    return
            if status in ExecutionStatus.TERMINAL:
                return

            while True:
                if await request.is_disconnected():
                    return
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=15)
                except asyncio.TimeoutError:
                    yield ": keep-alive\n\n"
                    continue
                if event["id"] <= seen:
                    continue
                seen = event["id"]
                yield frame(event)
                if event["type"] in TERMINAL_EVENTS:
                    return
        finally:
            bus.unsubscribe(key, queue)

    return StreamingResponse(
        generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no", "Connection": "keep-alive"},
    )
