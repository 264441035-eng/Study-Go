from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_create_and_list_task() -> None:
    resp = client.post("/api/tasks", json={"title": "英語の勉強", "done": False})
    assert resp.status_code == 201
    body = resp.json()
    assert body["title"] == "英語の勉強"
    assert body["done"] is False
    assert "id" in body

    resp = client.get("/api/tasks")
    assert resp.status_code == 200
    assert any(t["title"] == "英語の勉強" for t in resp.json())


def test_update_task() -> None:
    created = client.post("/api/tasks", json={"title": "数学の勉強", "done": False}).json()
    resp = client.patch(f"/api/tasks/{created['id']}", json={"title": "数学の勉強", "done": True})
    assert resp.status_code == 200
    assert resp.json()["done"] is True
