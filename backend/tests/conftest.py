import os

os.environ["DATABASE_URL"] = "sqlite+pysqlite:///:memory:"
os.environ["JWT_SECRET"] = "test-secret"
os.environ["CORS_ORIGINS"] = "http://testserver"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import StaticPool, create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base, Category
from app.db.session import get_db
from app.main import app

engine = create_engine("sqlite+pysqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)

@pytest.fixture(autouse=True)
def reset_db():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    db = TestingSession()
    for name in ["Food", "Transport", "Housing", "Shopping", "Health", "Entertainment", "Bills", "Other"]:
        db.add(Category(name=name))
    db.commit(); db.close()
    yield

@pytest.fixture
def client():
    def override():
        db = TestingSession()
        try: yield db
        finally: db.close()
    app.dependency_overrides[get_db] = override
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()

@pytest.fixture
def registered(client):
    response = client.post("/api/auth/register", json={"email":"alice@example.com","password":"password123"})
    assert response.status_code == 201
    return response.json()["access_token"]

@pytest.fixture
def auth_headers(registered):
    return {"Authorization": f"Bearer {registered}"}
