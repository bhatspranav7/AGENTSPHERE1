import asyncio
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

# Core
from .core.config import settings
from .core.logging import get_logger, setup_logging

# -------------------------------------------------
# LOGGING (MUST BE FIRST)
# -------------------------------------------------
setup_logging()

from .api.executions import router as executions_router  # noqa: E402
from .api.system import router as system_router  # noqa: E402
from .db.init_db import init_db  # noqa: E402
from .services.events import bus  # noqa: E402
from .services.runner import recover_interrupted_runs, runner  # noqa: E402


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    recover_interrupted_runs()
    bus.bind_loop(asyncio.get_running_loop())
    get_logger().info("AgentSphere ready")
    yield
    runner.shutdown()


# -------------------------------------------------
# APP INITIALIZATION
# -------------------------------------------------
app = FastAPI(
    title="AgentSphere",
    description="Autonomous multi-agent workflow system: planner, DAG orchestrator, supervised agents, full audit trail.",
    version="2.0.0",
    lifespan=lifespan,
)

# -------------------------------------------------
# MIDDLEWARE
# -------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials="*" not in settings.cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------------------------------------
# ROUTERS (root for curl/Swagger, /api for the UI)
# -------------------------------------------------
for router in (executions_router, system_router):
    app.include_router(router)
    app.include_router(router, prefix="/api", include_in_schema=False)

# -------------------------------------------------
# FRONTEND (single-service deployment)
# -------------------------------------------------
frontend = Path(settings.FRONTEND_DIR).resolve()
index = frontend / "index.html"

if index.is_file():
    app.mount("/assets", StaticFiles(directory=frontend / "assets"), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    def spa(full_path: str):
        if full_path.startswith("api/"):
            raise HTTPException(status_code=404, detail="Not found")
        candidate = (frontend / full_path).resolve()
        if full_path and candidate.is_file() and frontend in candidate.parents:
            return FileResponse(candidate)
        return FileResponse(index)
else:
    @app.get("/", include_in_schema=False)
    def root():
        return {"service": "AgentSphere", "docs": "/docs", "health": "/health"}
