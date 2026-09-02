from fastapi.testclient import TestClient

from app.auth import verify_token
from app.config import Settings, get_settings
from app.main import app

client = TestClient(app)


def teardown_function():
    app.dependency_overrides.clear()


def test_dev_token_issues_verifiable_token():
    resp = client.post("/dev/token", json={"user_id": "demo-student"})
    assert resp.status_code == 200
    token = resp.json()["token"]
    assert verify_token(token, get_settings()) == "demo-student"


def test_dev_token_hidden_outside_local():
    app.dependency_overrides[get_settings] = lambda: Settings(app_env="prod")
    resp = client.post("/dev/token", json={"user_id": "x"})
    assert resp.status_code == 404
