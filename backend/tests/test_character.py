from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_create_and_list_character() -> None:
    resp = client.post("/api/characters", json={"name": "Hero", "level": 1, "hp": 100})
    assert resp.status_code == 201
    body = resp.json()
    assert body["name"] == "Hero"
    assert "id" in body

    resp = client.get("/api/characters")
    assert resp.status_code == 200
    assert any(c["name"] == "Hero" for c in resp.json())


def test_get_character_by_id() -> None:
    created = client.post("/api/characters", json={"name": "Mage", "level": 3, "hp": 80}).json()
    resp = client.get(f"/api/characters/{created['id']}")
    assert resp.status_code == 200
    assert resp.json()["name"] == "Mage"
