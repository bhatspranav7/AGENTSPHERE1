from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.api.executions import router as executions_router

# -------------------------------------------------
# APP INITIALIZATION
# -------------------------------------------------

app = FastAPI(
    title="AgentSphere",
    description="Enterprise-grade Autonomous Multi-Agent Workflow System",
    version="1.1.0",
)

# -------------------------------------------------
# MIDDLEWARE
# -------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # tighten later when UI is fixed
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------------------------------------
# ROUTERS
# -------------------------------------------------

app.include_router(executions_router)

# -------------------------------------------------
# HEALTH CHECK
# -------------------------------------------------

@app.get("/")
def health_check():
    return {
        "status": "running",
        "service": "AgentSphere",
        "message": "AgentSphere backend running 🚀"
    }
