from fastapi import FastAPI
from app.db.base import Base
from app.db.session import engine

app = FastAPI(
    title="AgentSphere",
    description="Autonomous Multi-Agent Workflow Automation System",
    version="0.1.0"
)

@app.on_event("startup")
def startup():
    if engine:
        Base.metadata.create_all(bind=engine)

@app.get("/")
def health_check():
    return {"status": "AgentSphere backend is alive 🚀"}
