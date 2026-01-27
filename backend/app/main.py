from fastapi import FastAPI

from app.db.base import Base
from app.db.session import engine
from app.api.routes import router


app = FastAPI(
    title="AgentSphere",
    description="Autonomous Multi-Agent Workflow Automation System",
    version="0.1.0",
)


@app.on_event("startup")
def on_startup():
    """
    Application startup hook.
    - Ensures database tables are created
    - Runs only after DB connection is available
    """
    if engine:
        Base.metadata.create_all(bind=engine)


# Register API routes
app.include_router(router, prefix="/api")


@app.get("/")
def health_check():
    """
    Health check endpoint for monitoring & load balancers
    """
    return {
        "status": "AgentSphere backend is alive 🚀",
        "service": "multi-agent-orchestrator"
    }
