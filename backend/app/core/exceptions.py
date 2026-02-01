from fastapi import HTTPException


class ExecutionError(Exception):
    """
    Raised when an execution fails internally.
    """
    pass


def execution_http_error(message: str) -> HTTPException:
    """
    Converts internal execution errors into safe HTTP errors.
    Prevents raw tracebacks from leaking to clients.
    """
    return HTTPException(
        status_code=500,
        detail={
            "error": message
        }
    )
