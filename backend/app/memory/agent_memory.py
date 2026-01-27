import redis
import json
from typing import Any, Dict, List
import os

REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))

redis_client = redis.Redis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    decode_responses=True
)

class AgentMemory:
    """
    Enterprise-grade agent memory using Redis.
    Supports short-term (workflow) and long-term (agent) memory.
    """

    @staticmethod
    def _workflow_key(workflow_id: str) -> str:
        return f"workflow_memory:{workflow_id}"

    @staticmethod
    def _agent_key(agent_name: str) -> str:
        return f"agent_memory:{agent_name}"

    @classmethod
    def save_workflow_memory(cls, workflow_id: str, data: Dict[str, Any]) -> None:
        redis_client.rpush(
            cls._workflow_key(workflow_id),
            json.dumps(data)
        )

    @classmethod
    def get_workflow_memory(cls, workflow_id: str) -> List[Dict[str, Any]]:
        entries = redis_client.lrange(cls._workflow_key(workflow_id), 0, -1)
        return [json.loads(e) for e in entries]

    @classmethod
    def save_agent_memory(cls, agent_name: str, data: Dict[str, Any]) -> None:
        redis_client.rpush(
            cls._agent_key(agent_name),
            json.dumps(data)
        )

    @classmethod
    def get_agent_memory(cls, agent_name: str, limit: int = 5) -> List[Dict[str, Any]]:
        entries = redis_client.lrange(cls._agent_key(agent_name), -limit, -1)
        return [json.loads(e) for e in entries]
