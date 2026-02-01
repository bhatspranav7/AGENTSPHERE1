from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Core
from backend.app.core.logging import setup_logging

# Routers
from backend.app.api.executions import router as executions_router
from backend.app.api.health import router as health_router

# -------------------------------------------------
# LOGGING (MUST BE FIRST)
# -------------------------------------------------
setup_logging()

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
app.include_router(health_router)
