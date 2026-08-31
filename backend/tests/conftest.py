import os

# The test suite must never depend on a developer's local backend/.env --
# it's meant for real local `uvicorn` runs (see docs/DEVELOPMENT.md), not
# for pytest. Without this, a developer with e.g. TTS_PROVIDER=gemini set
# locally would silently have every test in the suite make real, paid,
# rate-limited API calls instead of using the mocks the tests assume.
# Must run before any app module import below -- get_settings() is
# @lru_cache'd and several modules call it at import time.
for _provider_var in ("LLM_PROVIDER", "IMAGE_PROVIDER", "TTS_PROVIDER", "EMBEDDING_PROVIDER"):
    os.environ[_provider_var] = "mock"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models
from app.database import Base, get_db
from app.main import app


@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()


@pytest.fixture()
def client(db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()
