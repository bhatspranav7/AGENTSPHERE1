import logging
import sys
from typing import Optional


class ContextFilter(logging.Filter):
    def __init__(self, execution_id: Optional[str] = None, agent_name: Optional[str] = None):
        super().__init__()
        self.execution_id = execution_id
        self.agent_name = agent_name

    def filter(self, record: logging.LogRecord) -> bool:
        record.execution_id = self.execution_id or "-"
        record.agent_name = self.agent_name or "-"
        return True


def setup_logging():
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    handler = logging.StreamHandler(sys.stdout)

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | exec=%(execution_id)s | agent=%(agent_name)s | %(message)s"
    )

    handler.setFormatter(formatter)
    root_logger.handlers = [handler]


def get_logger(
    execution_id: Optional[str] = None,
    agent_name: Optional[str] = None,
) -> logging.Logger:
    logger = logging.getLogger("agentsphere")
    logger.addFilter(ContextFilter(execution_id, agent_name))
    return logger
