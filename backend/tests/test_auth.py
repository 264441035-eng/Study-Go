import json

import bcrypt
import jwt
import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

_SECRET = "test-secret"


def _hash(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


@pytest.fixture(autouse=True)
def auth_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """既知の ID/PW を AUTH_USERS に用意し、署名鍵も固定する。"""
    monkeypatch.setenv("JWT_SECRET", _SECRET)
    monkeypatch.setenv("AUTH_USERS", json.dumps({"student01": _hash("correct-pw")}))


def test_login_success_returns_valid_token() -> None:
    resp = client.post("/api/auth/login", json={"user_id": "student01", "password": "correct-pw"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["user_id"] == "student01"

    payload = jwt.decode(body["token"], _SECRET, algorithms=["HS256"])
    assert payload["user_id"] == "student01"


def test_login_wrong_password_is_401() -> None:
    resp = client.post("/api/auth/login", json={"user_id": "student01", "password": "wrong"})
    assert resp.status_code == 401


def test_login_unknown_user_is_401() -> None:
    resp = client.post("/api/auth/login", json={"user_id": "ghost", "password": "correct-pw"})
    assert resp.status_code == 401


def test_login_no_users_configured_is_401(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("AUTH_USERS", raising=False)
    resp = client.post("/api/auth/login", json={"user_id": "student01", "password": "correct-pw"})
    assert resp.status_code == 401
