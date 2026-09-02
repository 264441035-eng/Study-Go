from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_create_and_list_message() -> None:
    resp = client.post("/api/chat", json={"sender": "character", "content": "そろそろ勉強する?"})
    assert resp.status_code == 201
    body = resp.json()
    assert body["sender"] == "character"
    assert body["content"] == "そろそろ勉強する?"
    assert "id" in body

    resp = client.get("/api/chat")
    assert resp.status_code == 200
    assert any(m["content"] == "そろそろ勉強する?" for m in resp.json())


def test_ai_tutor_proxy_routes() -> None:
    with patch("app.routers.chat.httpx.Client") as mock_client:
        mock_client.return_value.__enter__.return_value.request.return_value = type(
            "Resp",
            (),
            {"status_code": 200, "json": lambda self: {"session_id": "s_123", "message": "はい、何を勉強しましたか？"}},
        )()

        resp = client.post("/api/chat/sessions", headers={"Authorization": "Bearer abc"})
        assert resp.status_code == 200
        assert resp.json()["session_id"] == "s_123"

        mock_client.return_value.__enter__.return_value.request.return_value = type(
            "Resp",
            (),
            {"status_code": 200, "json": lambda self: {"message": "いいですね", "state": "questioning"}},
        )()

        resp = client.post(
            "/api/chat/sessions/s_123/messages",
            headers={"Authorization": "Bearer abc"},
            json={"message": "一次関数"},
        )
        assert resp.status_code == 200
        assert resp.json()["state"] == "questioning"


def test_backend_allows_vite_localhost_ports() -> None:
    resp = client.get(
        "/api/chat",
        headers={"Origin": "http://localhost:5175"},
    )
    assert resp.status_code == 200
    assert resp.headers.get("access-control-allow-origin") == "http://localhost:5175"
