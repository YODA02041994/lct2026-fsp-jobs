import os, sys, tempfile
os.environ["FSP_DATABASE_URL"] = "sqlite:///" + os.path.join(tempfile.mkdtemp(), "test.db")
os.environ["FSP_SECRET_KEY"] = "test-secret"
os.environ["FSP_TEST_BLOCK_SIZE"] = "3"
os.environ["FSP_TEST_BLOCKS"] = "2"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="session")
def client():
    from app.main import app
    from app.db import init_db
    from app.seed import ensure_catalog, seed_demo
    init_db()
    ensure_catalog()
    seed_demo(n_candidates=40, rng_seed=3)
    with TestClient(app) as c:
        yield c


def register_and_confirm(client, email, role, password="password123"):
    r = client.post("/api/v1/auth/register", json={"email": email, "password": password, "role": role})
    assert r.status_code == 201, r.text
    token = r.json()["demo_confirm_url"].split("token=")[1]
    r = client.get("/api/v1/auth/confirm", params={"token": token})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}
