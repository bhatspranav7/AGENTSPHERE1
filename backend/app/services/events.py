"""Execution event log + live fan-out.

Workers (threads) call `publish`; the event is written to `execution_events`
first, then pushed onto the asyncio queues of any SSE subscribers. Because the
DB is the source of truth, a client can connect mid-run (or after the run) and
replay everything it missed before tailing live events.
"""
import asyncio
import logging
import threading
import uuid
from collections import defaultdict
from datetime import datetime

from ..db.session import SessionLocal
from ..models import ExecutionEvent

logger = logging.getLogger(__name__)

TERMINAL_EVENTS = {"execution.completed", "execution.failed", "execution.aborted", "execution.cancelled"}


class EventBus:
    def __init__(self):
        self._subscribers: dict[str, set[asyncio.Queue]] = defaultdict(set)
        self._lock = threading.Lock()
        self.loop: asyncio.AbstractEventLoop | None = None

    def bind_loop(self, loop: asyncio.AbstractEventLoop):
        self.loop = loop

    def publish(self, execution_id: uuid.UUID | str, type_: str, payload: dict | None = None) -> dict:
        execution_uuid = uuid.UUID(str(execution_id))
        db = SessionLocal()
        try:
            row = ExecutionEvent(execution_id=execution_uuid, type=type_, payload=payload or {},
                                 created_at=datetime.utcnow())
            db.add(row)
            db.commit()
            event = serialize(row)
        finally:
            db.close()

        key = str(execution_uuid)
        with self._lock:
            queues = list(self._subscribers.get(key, ()))
        if queues and self.loop is not None:
            for q in queues:
                self.loop.call_soon_threadsafe(q.put_nowait, event)
        return event

    def subscribe(self, execution_id: str) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue()
        with self._lock:
            self._subscribers[execution_id].add(q)
        return q

    def unsubscribe(self, execution_id: str, q: asyncio.Queue):
        with self._lock:
            subs = self._subscribers.get(execution_id)
            if subs:
                subs.discard(q)
                if not subs:
                    del self._subscribers[execution_id]


def serialize(row: ExecutionEvent) -> dict:
    return {
        "id": row.id,
        "execution_id": str(row.execution_id),
        "type": row.type,
        "payload": row.payload or {},
        "ts": (row.created_at or datetime.utcnow()).isoformat() + "Z",
    }


bus = EventBus()
