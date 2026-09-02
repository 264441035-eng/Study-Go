import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app.auth import AuthError, create_access_token, get_current_user_id, verify_token
from app.config import get_settings

settings = get_settings()

# 認証依存を検証するための最小アプリ
app = FastAPI()


@app.get("/whoami")
def whoami(user_id: str = Depends(get_current_user_id)):
    return {"user_id": user_id}


client = TestClient(app)


def test_create_and_verify_roundtrip():
    token = create_access_token("user123", settings)
    assert verify_token(token, settings) == "user123"


def test_verify_rejects_garbage():
    with pytest.raises(AuthError):
        verify_token("not-a-token", settings)


def test_protected_route_requires_token():
    assert client.get("/whoami").status_code == 401


def test_protected_route_with_valid_token():
    token = create_access_token("user123", settings)
    resp = client.get("/whoami", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json()["user_id"] == "user123"


def test_protected_route_rejects_bad_scheme():
    resp = client.get("/whoami", headers={"Authorization": "Token abc"})
    assert resp.status_code == 401
