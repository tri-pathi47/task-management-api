
import re
import warnings

from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import declarative_base, sessionmaker

from app.config import settings

database_url = make_url(settings.database_url)
malformed_local_host = (
    re.fullmatch(
        r"(?P<password_suffix>\d+)@localhost",
        database_url.host or "",
        flags=re.IGNORECASE,
    )
    if database_url.host
    else None
)
if malformed_local_host:
    warnings.warn(
        "DATABASE_URL contains an unescaped @ in its password. "
        "Treating the numeric host prefix as password text; percent-encode "
        "the @ as %40 in .env to remove this compatibility fix.",
        RuntimeWarning,
        stacklevel=2,
    )
    database_url = database_url.set(
        host="localhost",
        password=(
            f"{database_url.password}@"
            f"{malformed_local_host.group('password_suffix')}"
        ),
    )

engine = create_engine(
    database_url,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def initialize_database():
    if database_url.drivername.startswith("mysql") and database_url.database:
        server_engine = create_engine(
            database_url.set(database=""),
            pool_pre_ping=True,
        )
        try:
            database_name = server_engine.dialect.identifier_preparer.quote(
                database_url.database
            )
            with server_engine.begin() as connection:
                connection.exec_driver_sql(
                    f"CREATE DATABASE IF NOT EXISTS {database_name}"
                )
        finally:
            server_engine.dispose()

    Base.metadata.create_all(bind=engine)
