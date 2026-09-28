from fastapi import HTTPException


class ExecutionError(Exception):
    """
    Raised when an execution fails internally.
    """


class ExecutionAborted(ExecutionError):
    """Supervisor decided the workflow cannot continue."""


class ExecutionCancelled(ExecutionError):
    """A user cancelled the execution while it was running."""


class LLMError(Exception):
    """The LLM call failed or returned unusable output."""


def execution_http_error(message: str, status_code: int = 500) -> HTTPException:
    """
    Converts internal execution errors into safe HTTP errors.
    Prevents raw tracebacks from leaking to clients.
    """
    return HTTPException(status_code=status_code, detail={"error": message})
