from backend.app.db.engine import engine, Base

# Import ALL models so they register with SQLAlchemy metadata
from backend.app.models.execution import ExecutionRun
from backend.app.models.execution_plan import ExecutionPlan
from backend.app.models.agent_execution import AgentExecution


def init_db():
    print("📦 Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("✅ Database tables created successfully")


if __name__ == "__main__":
    init_db()
