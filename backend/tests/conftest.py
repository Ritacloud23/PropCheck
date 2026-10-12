"""Test setup.

* Uses the dedicated `propcheck_test` database, migrated once per run with Alembic (same schema as prod).
* Everything is async: one event loop for the whole run (see pytest-asyncio settings in pyproject.toml),
  an AsyncEngine on asyncpg, and an httpx.AsyncClient that calls the ASGI app in-process.
* Each test runs inside an outer transaction that is rolled back afterwards. Service-level
  `commit()` calls become SAVEPOINT releases, so tests are isolated and fast.
"""

import os
import tempfile

os.environ.setdefault("STORAGE_DIR", tempfile.mkdtemp(prefix="propcheck-test-storage-"))
os.environ["REDIS_URL"] = ""  # tests always use the in-memory limiter, reset per test

from app.config import settings  # noqa: E402

settings.database_url = settings.test_database_url  # before app.db creates its engine

import pytest  # noqa: E402
from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402
from sqlalchemy import text  # noqa: E402
from sqlalchemy.ext.asyncio import create_async_engine  # noqa: E402
from sqlmodel.ext.asyncio.session import AsyncSession  # noqa: E402

from app.db import get_session  # noqa: E402
from app.main import app  # noqa: E402
from app.services import ratelimit  # noqa: E402

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _upgrade(connection) -> None:
    cfg = Config(os.path.join(BACKEND_DIR, "alembic.ini"))
    cfg.set_main_option("script_location", os.path.join(BACKEND_DIR, "alembic"))
    cfg.attributes["connection"] = connection  # alembic/env.py migrates on this connection
    command.upgrade(cfg, "head")


@pytest.fixture(scope="session")
async def engine():
    eng = create_async_engine(settings.test_database_url)
    async with eng.begin() as conn:
        await conn.execute(text("DROP SCHEMA IF EXISTS public CASCADE"))
        await conn.execute(text("CREATE SCHEMA public"))
        await conn.run_sync(_upgrade)
    yield eng
    await eng.dispose()


def _session_on(connection) -> AsyncSession:
    return AsyncSession(bind=connection, join_transaction_mode="create_savepoint", expire_on_commit=False)


@pytest.fixture()
async def connection(engine):
    async with engine.connect() as conn:
        outer = await conn.begin()
        try:
            yield conn
        finally:
            await outer.rollback()


@pytest.fixture()
async def session(connection):
    """The test's own session (setup and assertions)."""
    db = _session_on(connection)
    try:
        yield db
    finally:
        await db.close()


@pytest.fixture()
async def client(connection):
    # Like app.db.get_session: a fresh session per request, so a request that rolls back never
    # expires objects the test is holding. All sessions share the test's connection/transaction.
    async def _override():
        async with _session_on(connection) as db:
            try:
                yield db
            except Exception:
                await db.rollback()
                raise

    app.dependency_overrides[get_session] = _override
    ratelimit.reset()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as c:
        yield c
    app.dependency_overrides.clear()
