from collections.abc import Generator

from sqlalchemy import Engine, create_engine, inspect, text
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings
from app.db.base import Base

settings = get_settings()

engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False} if settings.database_url.startswith("sqlite") else {},
)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, class_=Session)


def get_db_session() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    ensure_schema(engine)


def ensure_schema(bind: Engine) -> None:
    Base.metadata.create_all(bind=bind)
    validate_schema_compatibility(bind)


def validate_schema_compatibility(bind: Engine) -> None:
    inspector = inspect(bind)
    table_names = set(inspector.get_table_names())
    if "report_raw_meta" not in table_names:
        return

    columns = {column["name"] for column in inspector.get_columns("report_raw_meta")}
    if "dedupe_key" not in columns:
        # Old Step 2/early Step 3 databases need migration before ingest/publish can run safely.
        raise RuntimeError(
            "Old database schema detected: report_raw_meta.dedupe_key is missing. "
            "Run `alembic upgrade head` or recreate `data/app.db`."
        )
    if "summary_lines_json" not in columns:
        with bind.begin() as connection:
            connection.execute(text("ALTER TABLE report_raw_meta ADD COLUMN summary_lines_json JSON"))
