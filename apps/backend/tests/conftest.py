from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///./test_homelab.db")
os.environ.setdefault("SECRET_KEY", "test-secret-key-change-me-123456")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/15")
os.environ.setdefault("DOCKER_HOST", "tcp://127.0.0.1:65535")

from app.db.base import Base  # noqa: E402
from app.db.init_db import seed_services  # noqa: E402
from app.db.session import SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(autouse=True)
def reset_db() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        seed_services(db)


@pytest.fixture()
def client() -> TestClient:
    with TestClient(app) as test_client:
        yield test_client
