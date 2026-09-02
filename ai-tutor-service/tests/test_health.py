from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_ok():
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    # デフォルト(local)は全モード mock/memory であること
    assert body["modes"]["llm"] == "mock"
    assert body["modes"]["backend"] == "mock"
    assert body["modes"]["database"] == "memory"
    assert body["modes"]["rag"] == "mock"
