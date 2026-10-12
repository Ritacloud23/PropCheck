from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlmodel.ext.asyncio.session import AsyncSession

from app.config import settings

engine = create_async_engine(settings.database_url, pool_pre_ping=True)

# expire_on_commit=False: with AsyncSession, touching an expired attribute would need implicit
# (sync) IO. Every column default is Python-side, so committed objects are already up to date.
SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_session() -> AsyncIterator[AsyncSession]:
    """One session per request. Services commit explicitly; anything uncommitted is rolled back."""
    async with SessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
