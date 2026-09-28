import logging
import sys
from typing import Optional


class ContextAdapter(logging.LoggerAdapter):
    """Prefixes every record with execution / agent context."""

    def process(self, msg, kwargs):
        extra = kwargs.setdefault("extra", {})
        extra.update(self.extra)
        return msg, kwargs


class _DefaultContext(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, "execution_id"):
            record.execution_id = "-"
        if not hasattr(record, "agent_name"):
            record.agent_name = "-"
        return True


def setup_logging():
    handler = logging.StreamHandler(sys.stdout)
    handler.addFilter(_DefaultContext())
    handler.setFormatter(logging.Formatter(
        "%(asctime)s | %(levelname)s | exec=%(execution_id)s | agent=%(agent_name)s | %(name)s | %(message)s"
    ))

    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.handlers = [handler]

    # SQLAlchemy / HTTP client chatter drowns the orchestration logs
    for noisy in ("sqlalchemy.engine", "httpx", "urllib3"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


def get_logger(
    execution_id: Optional[str] = None,
    agent_name: Optional[str] = None,
) -> logging.LoggerAdapter:
    return ContextAdapter(
        logging.getLogger("agentsphere"),
        {"execution_id": execution_id or "-", "agent_name": agent_name or "-"},
    )
