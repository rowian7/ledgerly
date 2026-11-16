import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app


@pytest.fixture
def client():
    """A TestClient backed by a fresh in-memory SQLite database for each test."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,  # share one connection so the in-memory DB persists
    )
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    def override_get_db():
        db = TestSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def make_user(client, username="alice", password="correct-horse"):
    client.post("/api/auth/register", json={"username": username, "password": password})
    token = client.post("/api/auth/login", json={"username": username, "password": password}).json()[
        "access_token"
    ]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def auth(client):
    return make_user(client)
