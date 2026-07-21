from pathlib import Path

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool


def normalize_database_url(database_url: str, base_dir: Path) -> str:
    sqlite_prefix = "sqlite+pysqlite:///"
    if database_url.startswith(sqlite_prefix):
        raw_path = database_url[len(sqlite_prefix) :]
        if raw_path.startswith("./"):
            db_path = (base_dir / raw_path[2:]).resolve()
            db_path.parent.mkdir(parents=True, exist_ok=True)
            return sqlite_prefix + str(db_path)
    return database_url


def build_engine(database_url: str) -> Engine:
    engine_kwargs: dict = {"future": True}
    is_sqlite = database_url.startswith("sqlite")
    is_memory = ":memory:" in database_url

    if is_sqlite:
        # SQLite otherwise gives up on a contended writer after only five
        # seconds.  Keep the DB-API timeout and the PRAGMA below in sync.
        engine_kwargs["connect_args"] = {
            "check_same_thread": False,
            "timeout": 30,
        }
        if is_memory:
            engine_kwargs["poolclass"] = StaticPool

    engine = create_engine(database_url, **engine_kwargs)

    if is_sqlite:
        @event.listens_for(engine, "connect")
        def configure_sqlite(dbapi_connection, _connection_record) -> None:
            cursor = dbapi_connection.cursor()
            try:
                cursor.execute("PRAGMA busy_timeout = 30000")
            finally:
                cursor.close()

    return engine


def build_session_factory(database_url: str) -> sessionmaker[Session]:
    engine = build_engine(database_url)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
