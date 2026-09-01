from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_create_and_list_base() -> None:
    resp = client.post("/api/bases", json={"name": "Home", "level": 1})
    assert resp.status_code == 201
    body = resp.json()
    assert body["name"] == "Home"
    assert "id" in body

    resp = client.get("/api/bases")
    assert resp.status_code == 200
    assert any(b["name"] == "Home" for b in resp.json())


def test_get_base_by_id() -> None:
    created = client.post("/api/bases", json={"name": "Camp", "level": 2}).json()
    resp = client.get(f"/api/bases/{created['id']}")
    assert resp.status_code == 200
    assert resp.json()["name"] == "Camp"
