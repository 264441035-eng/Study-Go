from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_create_and_list_encounter() -> None:
    resp = client.post("/api/encounters", json={"partner_name": "野本"})
    assert resp.status_code == 201
    body = resp.json()
    assert body["partner_name"] == "野本"
    assert body["reward_claimed"] is False
    assert "id" in body

    resp = client.get("/api/encounters")
    assert resp.status_code == 200
    assert any(e["partner_name"] == "野本" for e in resp.json())
