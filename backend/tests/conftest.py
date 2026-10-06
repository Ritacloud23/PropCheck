"""Test setup.

* Uses the dedicated `propcheck_test` database, migrated once per run with Alembic (same schema as prod).
* Each test runs inside an outer transaction that is rolled back afterwards. Service-level
  `commit()` calls become SAVEPOINT releases, so tests are isolated and fast.
"""

import os
import tempfile

os.environ.setdefault("STORAGE_DIR", tempfile.mkdtemp(prefix="propcheck-test-storage-"))
os.environ["AUTH_RATE_LIMIT_PER_MINUTE"] = "1000"

from app.config import settings  # noqa: E402

settings.database_url = settings.test_database_url  # before app.db creates its engine

import pytest  # noqa: E402
from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine, text  # noqa: E402
from sqlmodel import Session  # noqa: E402

from app.db import get_session  # noqa: E402
from app.main import app  # noqa: E402
from app.services import ratelimit  # noqa: E402

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@pytest.fixture(scope="session")
def engine():
    eng = create_engine(settings.test_database_url)
    with eng.begin() as conn:
        conn.execute(text("DROP SCHEMA IF EXISTS public CASCADE"))
        conn.execute(text("CREATE SCHEMA public"))
    cfg = Config(os.path.join(BACKEND_DIR, "alembic.ini"))
    cfg.set_main_option("script_location", os.path.join(BACKEND_DIR, "alembic"))
    cfg.cmd_opts = type("Opts", (), {"x": [f"db_url={settings.test_database_url}"]})()
    command.upgrade(cfg, "head")
    yield eng
    eng.dispose()


@pytest.fixture()
def session(engine):
    connection = engine.connect()
    outer = connection.begin()
    db = Session(bind=connection, join_transaction_mode="create_savepoint")
    yield db
    db.close()
    outer.rollback()
    connection.close()


@pytest.fixture()
def client(session):
    def _override():
        try:
            yield session
        except Exception:
            session.rollback()
            raise

    app.dependency_overrides[get_session] = _override
    ratelimit.reset()
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
