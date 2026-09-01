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
