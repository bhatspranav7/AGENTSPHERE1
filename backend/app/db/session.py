import time
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import OperationalError

DATABASE_URL = "postgresql://agentsphere:agentsphere@postgres:5432/agentsphere_db"

engine = None

# Retry logic for Postgres startup
for i in range(10):
    try:
        engine = create_engine(DATABASE_URL)
        connection = engine.connect()
        connection.close()
        print("✅ Connected to PostgreSQL")
        break
    except OperationalError:
        print("⏳ PostgreSQL not ready, retrying...")
        time.sleep(2)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)
