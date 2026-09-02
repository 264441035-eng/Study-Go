import uuid

import jwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.dependencies import JWT_ALGORITHM, JWT_SECRET_KEY
from app.main import app
from app.models import User


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


def _create_user_and_token(db_session) -> tuple[User, str]:
    user = User(email=f"{uuid.uuid4()}@example.com")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    token = jwt.encode({"sub": str(user.id)}, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return user, token


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _valid_payload(**overrides) -> dict:
    payload = {
        "name": "Local Library",
        "category": "library",
        "latitude": 35.681236,
        "longitude": 139.767125,
    }
    payload.update(overrides)
    return payload


def test_create_and_list_base(client, db_session) -> None:
    _, token = _create_user_and_token(db_session)

    resp = client.post("/api/v1/bases", json=_valid_payload(), headers=_auth_headers(token))
    assert resp.status_code == 201
    body = resp.json()
    assert body["name"] == "Local Library"
    assert body["category"] == "library"
    assert "id" in body
    assert "latitude" in body and "longitude" in body

    resp = client.get("/api/v1/bases", headers=_auth_headers(token))
    assert resp.status_code == 200
    assert any(b["id"] == body["id"] for b in resp.json())


def test_get_and_delete_own_base(client, db_session) -> None:
    _, token = _create_user_and_token(db_session)
    created = client.post(
        "/api/v1/bases", json=_valid_payload(), headers=_auth_headers(token)
    ).json()

    resp = client.get(f"/api/v1/bases/{created['id']}", headers=_auth_headers(token))
    assert resp.status_code == 200

    resp = client.delete(f"/api/v1/bases/{created['id']}", headers=_auth_headers(token))
    assert resp.status_code == 204

    resp = client.get(f"/api/v1/bases/{created['id']}", headers=_auth_headers(token))
    assert resp.status_code == 404


def test_count_bases(client, db_session) -> None:
    _, token = _create_user_and_token(db_session)

    resp = client.get("/api/v1/bases/count", headers=_auth_headers(token))
    assert resp.status_code == 200
    assert resp.json() == {"count": 0}

    client.post("/api/v1/bases", json=_valid_payload(), headers=_auth_headers(token))
    client.post(
        "/api/v1/bases",
        json=_valid_payload(name="School", category="school"),
        headers=_auth_headers(token),
    )

    resp = client.get("/api/v1/bases/count", headers=_auth_headers(token))
    assert resp.status_code == 200
    assert resp.json() == {"count": 2}


def test_count_bases_only_counts_own(client, db_session) -> None:
    _, token_a = _create_user_and_token(db_session)
    _, token_b = _create_user_and_token(db_session)

    client.post("/api/v1/bases", json=_valid_payload(), headers=_auth_headers(token_a))

    resp = client.get("/api/v1/bases/count", headers=_auth_headers(token_b))
    assert resp.json() == {"count": 0}


def test_create_base_invalid_category(client, db_session) -> None:
    _, token = _create_user_and_token(db_session)

    resp = client.post(
        "/api/v1/bases",
        json=_valid_payload(category="cafe"),
        headers=_auth_headers(token),
    )
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
def test_create_base_invalid_coordinates(client, db_session, overrides) -> None:
    _, token = _create_user_and_token(db_session)

    resp = client.post(
        "/api/v1/bases", json=_valid_payload(**overrides), headers=_auth_headers(token)
    )
    assert resp.status_code == 400


@pytest.mark.parametrize("category", ["home", "school"])
def test_home_and_school_limited_to_one(client, db_session, category) -> None:
    _, token = _create_user_and_token(db_session)

    resp = client.post(
        "/api/v1/bases", json=_valid_payload(category=category), headers=_auth_headers(token)
    )
    assert resp.status_code == 201

    resp = client.post(
        "/api/v1/bases",
        json=_valid_payload(category=category, name="Second"),
        headers=_auth_headers(token),
    )
    assert resp.status_code == 400


@pytest.mark.parametrize("category", ["library", "cram_school"])
def test_library_and_cram_school_allow_multiple(client, db_session, category) -> None:
    _, token = _create_user_and_token(db_session)

    for i in range(3):
        resp = client.post(
            "/api/v1/bases",
            json=_valid_payload(category=category, name=f"Base {i}"),
            headers=_auth_headers(token),
        )
        assert resp.status_code == 201


def test_home_limit_is_per_user(client, db_session) -> None:
    _, token_a = _create_user_and_token(db_session)
    _, token_b = _create_user_and_token(db_session)

    resp = client.post(
        "/api/v1/bases", json=_valid_payload(category="home"), headers=_auth_headers(token_a)
    )
    assert resp.status_code == 201

    resp = client.post(
        "/api/v1/bases", json=_valid_payload(category="home"), headers=_auth_headers(token_b)
    )
    assert resp.status_code == 201


def test_cannot_access_other_users_base(client, db_session) -> None:
    _, token_a = _create_user_and_token(db_session)
    _, token_b = _create_user_and_token(db_session)

    created = client.post(
        "/api/v1/bases", json=_valid_payload(), headers=_auth_headers(token_a)
    ).json()

    resp = client.get(f"/api/v1/bases/{created['id']}", headers=_auth_headers(token_b))
    assert resp.status_code == 404

    resp = client.delete(f"/api/v1/bases/{created['id']}", headers=_auth_headers(token_b))
    assert resp.status_code == 404


def test_requires_authentication(client) -> None:
    resp = client.get("/api/v1/bases")
    assert resp.status_code in (401, 403)
