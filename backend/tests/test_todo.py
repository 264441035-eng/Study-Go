import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app


@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        app.dependency_overrides.clear()


@pytest.fixture()
def client(db_session):
    return TestClient(app)


def _valid_payload(**overrides) -> dict:
    payload = {
        "name": "英単語を10個覚える",
        "category": "study",
    }
    payload.update(overrides)
    return payload


def test_create_and_list_todo(client) -> None:
    resp = client.post("/api/v1/todos", json=_valid_payload())
    assert resp.status_code == 201
    body = resp.json()
    assert body["name"] == "英単語を10個覚える"
    assert body["category"] == "study"
    assert body["done"] is False
    assert "id" in body
    assert "created_at" in body

    resp = client.get("/api/v1/todos")
    assert resp.status_code == 200
    assert any(t["id"] == body["id"] for t in resp.json())


def test_create_todo_with_done_true(client) -> None:
    resp = client.post(
        "/api/v1/todos", json=_valid_payload(category="exercise", done=True)
    )
    assert resp.status_code == 201
    assert resp.json()["category"] == "exercise"
    assert resp.json()["done"] is True


def test_get_todo(client) -> None:
    created = client.post("/api/v1/todos", json=_valid_payload()).json()

    resp = client.get(f"/api/v1/todos/{created['id']}")
    assert resp.status_code == 200
    assert resp.json()["id"] == created["id"]


def test_get_missing_todo_returns_404(client) -> None:
    resp = client.get("/api/v1/todos/00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 404


def test_update_todo_status(client) -> None:
    created = client.post("/api/v1/todos", json=_valid_payload()).json()

    resp = client.patch(
        f"/api/v1/todos/{created['id']}/status", json={"done": True}
    )
    assert resp.status_code == 200
    assert resp.json()["done"] is True

    resp = client.patch(
        f"/api/v1/todos/{created['id']}/status", json={"done": False}
    )
    assert resp.status_code == 200
    assert resp.json()["done"] is False


def test_update_missing_todo_status_returns_404(client) -> None:
    resp = client.patch(
        "/api/v1/todos/00000000-0000-0000-0000-000000000000/status",
        json={"done": True},
    )
    assert resp.status_code == 404


def test_delete_todo(client) -> None:
    created = client.post("/api/v1/todos", json=_valid_payload()).json()

    resp = client.delete(f"/api/v1/todos/{created['id']}")
    assert resp.status_code == 204

    resp = client.get(f"/api/v1/todos/{created['id']}")
    assert resp.status_code == 404


def test_delete_missing_todo_returns_404(client) -> None:
    resp = client.delete("/api/v1/todos/00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 404


def test_create_todo_invalid_category(client) -> None:
    resp = client.post("/api/v1/todos", json=_valid_payload(category="cooking"))
    assert resp.status_code == 400


def test_create_todo_missing_name(client) -> None:
    resp = client.post("/api/v1/todos", json=_valid_payload(name=""))
    assert resp.status_code == 422
