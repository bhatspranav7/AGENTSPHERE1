from sqlalchemy.orm import sessionmaker
from app.db.engine import engine

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)
