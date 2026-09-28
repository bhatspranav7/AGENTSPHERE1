"""Schema bootstrap.

`create_all` creates missing tables but never alters existing ones. Databases
created by earlier versions of AgentSphere have fewer columns (and a Postgres
enum for status), so we add whatever is missing in place. Nothing is dropped.
"""
import logging

from sqlalchemy import inspect, text

from .session import Base, engine
from .. import models  # noqa: F401  (registers every table on Base.metadata)

logger = logging.getLogger(__name__)


def _upgrade_existing_tables():
    inspector = inspect(engine)
    existing = set(inspector.get_table_names())
    preparer = engine.dialect.identifier_preparer

    with engine.begin() as conn:
        for table in Base.metadata.sorted_tables:
            if table.name not in existing:
                continue

            current = {c["name"]: c for c in inspector.get_columns(table.name)}
            for column in table.columns:
                if column.name in current:
                    continue
                col_type = column.type.compile(dialect=engine.dialect)
                conn.execute(text(
                    f"ALTER TABLE {preparer.quote(table.name)} ADD COLUMN {preparer.quote(column.name)} {col_type}"
                ))
                logger.info("Added column %s.%s", table.name, column.name)

        # v1 stored status as a Postgres ENUM with only 4 values
        if engine.dialect.name == "postgresql" and "execution_runs" in existing:
            row = conn.execute(text(
                "SELECT data_type FROM information_schema.columns "
                "WHERE table_name = 'execution_runs' AND column_name = 'status'"
            )).scalar()
            if row == "USER-DEFINED":
                conn.execute(text(
                    "ALTER TABLE execution_runs ALTER COLUMN status TYPE VARCHAR(20) USING status::text"
                ))
                logger.info("Converted execution_runs.status enum to VARCHAR")


def init_db():
    Base.metadata.create_all(bind=engine)
    _upgrade_existing_tables()
    logger.info("Database schema ready")


if __name__ == "__main__":
    init_db()
