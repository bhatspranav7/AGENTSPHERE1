import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# -------------------------------------------------
# DATABASE CONFIGURATION
# -------------------------------------------------

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://agentsphere:agentsphere@localhost:5432/agentsphere_db",
)

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

Base = declarative_base()
