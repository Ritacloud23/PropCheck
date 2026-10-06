from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlmodel import Session

from app.config import settings

engine = create_engine(settings.database_url, pool_pre_ping=True)


def get_session() -> Iterator[Session]:
    """One session per request. Services commit explicitly; anything uncommitted is rolled back."""
    with Session(engine) as session:
        try:
            yield session
        except Exception:
            session.rollback()
            raise
