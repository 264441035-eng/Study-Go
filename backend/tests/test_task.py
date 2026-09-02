import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models import Character, StudyBase
from app.routers import task as task_router

client = TestClient(app)


@pytest.fixture()
def db_session():
    """拠点との連携をテストするためのDB（SQLite）を用意し、get_dbを差し替える。"""
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


def setup_function() -> None:
    """各テストの前に状態を初期化する。"""

    for task in task_router._study_tasks:
        task.done = False

    for task in task_router._exercise_tasks:
        task.done = False

    task_router._study_records.clear()

    task_router._study_started_at = None

    task_router._status_date = task_router._now().date()


def test_get_study_tasks() -> None:
    resp = client.get(
        "/api/tasks/study",
        params={"level": 1},
    )

    assert resp.status_code == 200

    body = resp.json()

    assert len(body) >= 1
    assert body[0]["title"] == "30秒勉強する（デモ）"
    assert body[0]["done"] is False


def test_study_time_and_auto_completion() -> None:
    resp = client.post("/api/tasks/study/start")

    assert resp.status_code == 201

    resp = client.post(
        "/api/tasks/study/time",
        json={"seconds": 30},
    )

    assert resp.status_code == 200

    body = resp.json()

    assert body["session_seconds"] == 30
    assert body["today_seconds"] == 30
    assert 1 in body["auto_completed_task_ids"]

    resp = client.get(
        "/api/tasks/context/study-status"
    )

    assert resp.status_code == 200

    tasks = resp.json()

    task = next(
        t for t in tasks
        if t["id"] == 1
    )

    assert task["done"] is True


def test_update_study_task_status() -> None:
    resp = client.post(
        "/api/tasks/study/2/status",
        json={"done": True},
    )

    assert resp.status_code == 200
    assert resp.json()["done"] is True


def test_update_exercise_task_status() -> None:
    resp = client.post(
        "/api/tasks/exercise/102/status",
        json={"done": True},
    )

    assert resp.status_code == 200
    assert resp.json()["done"] is True


def test_update_study_task_status_not_found() -> None:
    resp = client.post(
        "/api/tasks/study/9999/status",
        json={"done": True},
    )

    assert resp.status_code == 404


def test_update_exercise_task_status_not_found() -> None:
    resp = client.post(
        "/api/tasks/exercise/9999/status",
        json={"done": True},
    )

    assert resp.status_code == 404


def test_start_study_twice_conflicts() -> None:
    resp = client.post("/api/tasks/study/start")

    assert resp.status_code == 201

    resp = client.post("/api/tasks/study/start")

    assert resp.status_code == 409


def test_send_study_time_without_start() -> None:
    resp = client.post(
        "/api/tasks/study/time",
        json={"seconds": 30},
    )

    assert resp.status_code == 400


def test_send_study_time_invalid_seconds() -> None:
    client.post("/api/tasks/study/start")

    resp = client.post(
        "/api/tasks/study/time",
        json={"seconds": 0},
    )

    assert resp.status_code == 422

    resp = client.post(
        "/api/tasks/study/time",
        json={"seconds": 86401},
    )

    assert resp.status_code == 422


def test_send_study_time_should_rest() -> None:
    client.post("/api/tasks/study/start")

    resp = client.post(
        "/api/tasks/study/time",
        json={"seconds": 50 * 60},
    )

    assert resp.status_code == 200
    assert resp.json()["should_rest"] is True


def test_send_study_time_adds_minutes_to_demo_character(db_session) -> None:
    """Task APIの秒数が分へ変換され、Character DBへ加算される。"""
    client.post("/api/tasks/study/start")

    response = client.post(
        "/api/tasks/study/time",
        json={"seconds": 125},
    )

    assert response.status_code == 200
    characters = db_session.query(Character).all()
    assert len(characters) == 1
    assert characters[0].name == "Demo Character"
    assert characters[0].total_study_minutes == 2
    assert characters[0].effective_study_minutes == 2


def test_send_study_time_updates_existing_character(db_session) -> None:
    """既存のCharacterがある場合、新規作成せず同じ1体へ加算する。"""
    character = Character(name="Existing Character")
    db_session.add(character)
    db_session.commit()

    client.post("/api/tasks/study/start")
    response = client.post(
        "/api/tasks/study/time",
        json={"seconds": 60},
    )

    assert response.status_code == 200
    db_session.refresh(character)
    assert db_session.query(Character).count() == 1
    assert character.total_study_minutes == 1


def test_send_subminute_study_time_does_not_create_character(db_session) -> None:
    """分未満を切り捨てた結果が0分ならCharacterを更新しない。"""
    client.post("/api/tasks/study/start")
    response = client.post(
        "/api/tasks/study/time",
        json={"seconds": 30},
    )

    assert response.status_code == 200
    assert db_session.query(Character).count() == 0


def test_list_study_tasks_filtered_by_level() -> None:
    resp = client.get(
        "/api/tasks/study",
        params={"level": 1},
    )

    assert resp.status_code == 200

    body = resp.json()

    assert all(task["required_level"] <= 1 for task in body)
    assert not any(task["id"] == 2 for task in body)


def test_list_exercise_tasks_filtered_by_level() -> None:
    resp = client.get(
        "/api/tasks/exercise",
        params={"level": 1},
    )

    assert resp.status_code == 200

    body = resp.json()

    assert all(task["required_level"] <= 1 for task in body)
    assert not any(task["id"] == 103 for task in body)


# =========================================================
# 位置情報による拠点への勉強時間の紐付け
# =========================================================


def _create_base(db_session, **overrides) -> StudyBase:
    base = StudyBase(
        name=overrides.get("name", "Test Base"),
        category=overrides.get("category", "library"),
        latitude=overrides.get("latitude", 35.681236),
        longitude=overrides.get("longitude", 139.767125),
    )
    db_session.add(base)
    db_session.commit()
    db_session.refresh(base)
    return base


def test_send_study_time_credits_nearby_base(db_session) -> None:
    base = _create_base(db_session)

    client.post("/api/tasks/study/start")

    resp = client.post(
        "/api/tasks/study/time",
        json={
            "seconds": 1800,
            "latitude": 35.681300,
            "longitude": 139.767200,
        },
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["matched_base_id"] == str(base.id)
    assert body["base_level"] == 1
    assert body["base_leveled_up"] is False


def test_send_study_time_ignores_far_away_base(db_session) -> None:
    _create_base(db_session)

    client.post("/api/tasks/study/start")

    resp = client.post(
        "/api/tasks/study/time",
        json={
            "seconds": 1800,
            # 遠く離れた座標（大阪付近）なので拠点にはマッチしない
            "latitude": 34.693725,
            "longitude": 135.502254,
        },
    )

    assert resp.status_code == 200
    assert resp.json()["matched_base_id"] is None


def test_send_study_time_without_location_does_not_credit_base(db_session) -> None:
    _create_base(db_session)

    client.post("/api/tasks/study/start")

    resp = client.post(
        "/api/tasks/study/time",
        json={"seconds": 1800},
    )

    assert resp.status_code == 200
    assert resp.json()["matched_base_id"] is None
