import os
import tempfile
from pathlib import Path

import pytest

_d = tempfile.mkdtemp()
os.environ["METADATA_DB_PATH"] = str(Path(_d) / "metadata.db")
os.environ["ANALYTICS_DB_PATH"] = str(Path(_d) / "analytics.db")
os.environ["AUTH_DEMO_MODE"] = "true"

from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import app

get_settings.cache_clear()


@pytest.fixture
def client() -> TestClient:
    with TestClient(app) as c:
        yield c


@pytest.fixture
def token(client: TestClient) -> str:
    r = client.post("/api/auth/login", json={"username": "tuser", "password": "x"})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


@pytest.fixture
def auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}
