from sqlalchemy import create_engine
import os

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://agentsphere:agentsphere@postgres:5432/agentsphere_db"
)

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True
)
