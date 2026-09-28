import logging
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

from ..core.config import settings
from ..db.session import SessionLocal
from ..models import ExecutionRun, ExecutionStatus
from ..orchestrator.engine import Orchestrator
from .events import bus

logger = logging.getLogger(__name__)


class ExecutionRunner:
    """Bounded worker pool. Runs beyond WORKER_THREADS wait in `queued`."""

    def __init__(self):
        self.pool = ThreadPoolExecutor(max_workers=settings.WORKER_THREADS, thread_name_prefix="exec")
        self._cancels: dict[str, threading.Event] = {}
        self._lock = threading.Lock()

    def submit(self, execution_id: uuid.UUID, objective: str, chaos: str):
        cancel = threading.Event()
        with self._lock:
            self._cancels[str(execution_id)] = cancel
        self.pool.submit(self._run, execution_id, objective, chaos, cancel)

    def _run(self, execution_id, objective, chaos, cancel):
        try:
            Orchestrator(execution_id, objective, chaos, cancel).run()
        except Exception:
            logger.exception("Orchestrator crashed outside its own error handling")
        finally:
            with self._lock:
                self._cancels.pop(str(execution_id), None)

    def cancel(self, execution_id: str) -> bool:
        with self._lock:
            event = self._cancels.get(execution_id)
        if event is None:
            return False
        event.set()
        return True

    def active_count(self) -> int:
        with self._lock:
            return len(self._cancels)

    def shutdown(self):
        with self._lock:
            for event in self._cancels.values():
                event.set()
        self.pool.shutdown(wait=False, cancel_futures=True)


def recover_interrupted_runs():
    """Runs left active by a crash/redeploy can never finish; close them out."""
    db = SessionLocal()
    try:
        stuck = db.query(ExecutionRun).filter(ExecutionRun.status.in_(ExecutionStatus.ACTIVE)).all()
        for run in stuck:
            run.status = ExecutionStatus.FAILED
            run.error = "Interrupted by server restart"
            run.finished_at = datetime.utcnow()
        db.commit()
        for run in stuck:
            bus.publish(run.execution_id, "execution.failed", {"reason": run.error})
        if stuck:
            logger.warning("Marked %d interrupted executions as failed", len(stuck))
    finally:
        db.close()


runner = ExecutionRunner()
