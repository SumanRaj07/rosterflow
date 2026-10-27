import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Point the app at a throwaway DB BEFORE importing it (engine is built at import).
os.environ["DATABASE_URL"] = "sqlite:///./test_rosterflow.db"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app import seed as seed_mod  # noqa: E402
from app.db import Base, SessionLocal, engine, get_db  # noqa: E402


@pytest.fixture(scope="module")
def client():
    if os.path.exists("test_rosterflow.db"):
        os.remove("test_rosterflow.db")
    from app.main import app
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    seed_mod.run(db)
    db.close()

    def _override():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = _override
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def login(client, email, password):
    r = client.post("/api/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return r.json()["token"]


@pytest.fixture(scope="module")
def admin_token(client):
    return login(client, "admin@rosterflow.local", "Admin@123")


@pytest.fixture(scope="module")
def manager_token(client):
    return login(client, "manager@rosterflow.local", "Manager@123")


@pytest.fixture(scope="module")
def employee_token(client):
    # first employee user (Aarav Sharma, EMP001)
    return login(client, "aarav.sharma@example.com", "Emp@123")
