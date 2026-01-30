from abc import ABC, abstractmethod


class BaseExecutionAgent(ABC):
    """
    Base class for all execution agents.
    """

    agent_name: str

    @abstractmethod
    def execute(self, execution_id, step):
        """
        Execute a single plan step.
        """
        pass
