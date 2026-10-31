"""Initialize new databases and upgrade existing databases before serving requests."""
import logging
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import inspect

from app.infrastructure.db.base import Base

logger = logging.getLogger(__name__)


def initialize_database(engine, config_path: Path) -> None:
    backend_dir = Path(__file__).resolve().parents[3]
    config = Config(str(backend_dir / "alembic.ini"))
    config.set_main_option("script_location", str(backend_dir / "migrations"))
    config.set_main_option("mlops.config_path", str(config_path))
    config.attributes["configure_logging"] = False
    with engine.connect() as connection:
        # Serialize startup schema changes across SQLite worker processes.
        if engine.dialect.name == "sqlite":
            connection.exec_driver_sql("BEGIN IMMEDIATE")
        else:
            connection.begin()
        try:
            config.attributes["connection"] = connection
            tables = set(inspect(connection).get_table_names())
            if not tables:
                Base.metadata.create_all(connection)
                command.stamp(config, "head")
            elif "alembic_version" not in tables:
                # Older create_all databases may be unversioned. Only baseline a
                # complete current schema; never mark an incomplete schema current.
                for table in Base.metadata.sorted_tables:
                    if table.name not in tables:
                        raise RuntimeError("Unversioned database is missing table: " + table.name)
                    columns = {item["name"] for item in inspect(connection).get_columns(table.name)}
                    if set(table.columns.keys()) - columns:
                        raise RuntimeError("Unversioned database has outdated table: " + table.name)
                command.stamp(config, "head")
            else:
                command.upgrade(config, "head")
            connection.commit()
        except Exception:
            connection.rollback()
            logger.exception("Automatic database migration failed; startup stopped")
            raise
