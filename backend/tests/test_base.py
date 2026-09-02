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
        "name": "Local Library",
        "category": "library",
        "latitude": 35.681236,
        "longitude": 139.767125,
    }
    payload.update(overrides)
    return payload


def test_create_and_list_base(client) -> None:
    resp = client.post("/api/v1/bases", json=_valid_payload())
    assert resp.status_code == 201
    body = resp.json()
    assert body["name"] == "Local Library"
    assert body["category"] == "library"
    assert "id" in body
    assert "latitude" in body and "longitude" in body

    resp = client.get("/api/v1/bases")
    assert resp.status_code == 200
    assert any(b["id"] == body["id"] for b in resp.json())


def test_get_and_delete_base(client) -> None:
    created = client.post("/api/v1/bases", json=_valid_payload()).json()

    resp = client.get(f"/api/v1/bases/{created['id']}")
    assert resp.status_code == 200

    resp = client.delete(f"/api/v1/bases/{created['id']}")
    assert resp.status_code == 204

    resp = client.get(f"/api/v1/bases/{created['id']}")
    assert resp.status_code == 404


def test_get_and_delete_missing_base_returns_404(client) -> None:
    resp = client.get("/api/v1/bases/00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 404

    resp = client.delete("/api/v1/bases/00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 404


def test_count_bases(client) -> None:
    resp = client.get("/api/v1/bases/count")
    assert resp.status_code == 200
    assert resp.json() == {"count": 0}

    client.post("/api/v1/bases", json=_valid_payload())
    client.post("/api/v1/bases", json=_valid_payload(name="School", category="school"))

    resp = client.get("/api/v1/bases/count")
    assert resp.status_code == 200
    assert resp.json() == {"count": 2}


def test_create_base_invalid_category(client) -> None:
    resp = client.post("/api/v1/bases", json=_valid_payload(category="cafe"))
    assert resp.status_code == 400


@pytest.mark.parametrize(
    "overrides",
    [
        {"latitude": 91},
        {"latitude": -91},
        {"longitude": 181},
        {"longitude": -181},
    ],
)
def test_create_base_invalid_coordinates(client, overrides) -> None:
    resp = client.post("/api/v1/bases", json=_valid_payload(**overrides))
    assert resp.status_code == 400


@pytest.mark.parametrize("category", ["home", "school"])
def test_home_and_school_limited_to_one(client, category) -> None:
    resp = client.post("/api/v1/bases", json=_valid_payload(category=category))
    assert resp.status_code == 201

    resp = client.post(
        "/api/v1/bases", json=_valid_payload(category=category, name="Second")
    )
    assert resp.status_code == 400


@pytest.mark.parametrize("category", ["library", "cram_school"])
def test_library_and_cram_school_allow_multiple(client, category) -> None:
    for i in range(3):
        resp = client.post(
            "/api/v1/bases", json=_valid_payload(category=category, name=f"Base {i}")
        )
        assert resp.status_code == 201


def test_create_base_starts_at_level_one(client) -> None:
    resp = client.post("/api/v1/bases", json=_valid_payload())
    body = resp.json()
    assert body["total_study_seconds"] == 0
    assert body["level"] == 1


def test_add_study_time_accumulates_and_levels_up(client) -> None:
    created = client.post("/api/v1/bases", json=_valid_payload()).json()

    resp = client.post(
        f"/api/v1/bases/{created['id']}/study-time", json={"seconds": 1800}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_study_seconds"] == 1800
    assert body["level"] == 1
    assert body["leveled_up"] is False

    resp = client.post(
        f"/api/v1/bases/{created['id']}/study-time", json={"seconds": 1800}
    )
    body = resp.json()
    assert body["total_study_seconds"] == 3600
    assert body["level"] == 2
    assert body["leveled_up"] is True


def test_add_study_time_rejects_non_positive_seconds(client) -> None:
    created = client.post("/api/v1/bases", json=_valid_payload()).json()

    resp = client.post(
        f"/api/v1/bases/{created['id']}/study-time", json={"seconds": 0}
    )
    assert resp.status_code == 422


def test_add_study_time_for_missing_base_returns_404(client) -> None:
    resp = client.post(
        "/api/v1/bases/00000000-0000-0000-0000-000000000000/study-time",
        json={"seconds": 600},
    )
    assert resp.status_code == 404
