from datetime import date, datetime
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from app.main import app
from app.models import Character
from app.routers import character as character_router
from app.routers import task as task_router

client = TestClient(app)


def make_character(**overrides) -> Character:
    """育成計算の単体テストで利用する未保存のCharacterを作る。"""
    values = {
        "id": uuid4(),
        "name": "Test Character",
        "total_study_minutes": 0,
        "total_penalty_minutes": 0,
        "effective_study_minutes": 0,
        "level": 1,
        "highest_level": 1,
        "minimum_level": 1,
        "evolution_stage": 0,
        "remaining_minutes_to_next_level": 0,
        "last_studied_at": None,
        "penalty_applied_through": None,
    }
    values.update(overrides)
    return Character(**values)


def test_create_character_saves_initial_state() -> None:
    response = client.post("/api/characters", json={"name": "Hero"})

    assert response.status_code == 201
    body = response.json()
    assert UUID(body["id"])
    assert body["name"] == "Hero"
    assert "hp" not in body
    assert body["level"] == 1
    assert body["highest_level"] == 1
    assert body["minimum_level"] == 1
    assert body["evolution_stage"] == 0
    assert body["total_study_minutes"] == 0
    assert body["total_penalty_minutes"] == 0
    assert body["effective_study_minutes"] == 0
    assert body["remaining_minutes_to_next_level"] > 0
    assert body["last_studied_at"] is None


def test_created_character_can_be_read_from_database() -> None:
    created = client.post("/api/characters", json={"name": "Mage"}).json()

    response = client.get(f"/api/characters/{created['id']}")

    assert response.status_code == 200
    assert response.json()["id"] == created["id"]
    assert response.json()["name"] == "Mage"


def test_list_characters_reads_database_records() -> None:
    first = client.post("/api/characters", json={"name": "Hero"}).json()
    second = client.post("/api/characters", json={"name": "Mage"}).json()

    response = client.get("/api/characters")

    assert response.status_code == 200
    character_ids = {character["id"] for character in response.json()}
    assert character_ids == {first["id"], second["id"]}


def test_create_character_rejects_empty_name() -> None:
    response = client.post("/api/characters", json={"name": ""})

    assert response.status_code == 422


def test_get_unknown_character_returns_404() -> None:
    response = client.get(f"/api/characters/{uuid4()}")

    assert response.status_code == 404
    assert response.json()["detail"] == "Character not found"


def test_record_study_persists_character_progress() -> None:
    created = client.post("/api/characters", json={"name": "Scholar"}).json()

    response = client.post(
        f"/api/characters/{created['id']}/study",
        json={"minutes": 5},
    )

    assert response.status_code == 200
    assert response.json()["total_study_minutes"] == 5
    assert response.json()["effective_study_minutes"] == 5
    assert response.json()["last_studied_at"].endswith("+09:00")

    fetched = client.get(f"/api/characters/{created['id']}")
    assert fetched.status_code == 200
    assert fetched.json()["total_study_minutes"] == 5


def test_record_study_rejects_non_positive_minutes() -> None:
    created = client.post("/api/characters", json={"name": "Scholar"}).json()

    response = client.post(
        f"/api/characters/{created['id']}/study",
        json={"minutes": 0},
    )

    assert response.status_code == 422


def test_reset_returns_character_to_initial_state() -> None:
    created = client.post("/api/characters", json={"name": "Resetter"}).json()
    minutes_to_level_10 = character_router.LEVEL_THRESHOLDS[9]
    client.post(
        f"/api/characters/{created['id']}/study",
        json={"minutes": minutes_to_level_10},
    )

    response = client.post(f"/api/characters/{created['id']}/reset")

    assert response.status_code == 200
    body = response.json()
    assert body["total_study_minutes"] == 0
    assert body["effective_study_minutes"] == 0
    assert body["level"] == 1
    assert body["highest_level"] == 1
    assert body["minimum_level"] == 1
    assert body["evolution_stage"] == 0
    assert body["last_studied_at"] is None

    fetched = client.get(f"/api/characters/{created['id']}")
    assert fetched.json()["level"] == 1
    assert fetched.json()["total_study_minutes"] == 0


def test_reset_unknown_character_returns_404() -> None:
    response = client.post(f"/api/characters/{uuid4()}/reset")

    assert response.status_code == 404


def test_reset_also_clears_today_study_time() -> None:
    """レベルリセット後は、今日の勉強時間（メモリ保持の勉強セッション）も0に戻る。"""
    task_router._study_records.clear()
    task_router._study_started_at = None
    try:
        created = client.post("/api/characters", json={"name": "Resetter2"}).json()

        client.post("/api/tasks/study/start")
        client.post("/api/tasks/study/time", json={"seconds": 120})
        before = client.get("/api/tasks/context/study-time").json()
        assert before["today_seconds"] > 0

        response = client.post(f"/api/characters/{created['id']}/reset")
        assert response.status_code == 200

        after = client.get("/api/tasks/context/study-time").json()
        assert after["today_seconds"] == 0
    finally:
        task_router._study_records.clear()
        task_router._study_started_at = None


def test_study_time_reaches_evolution_level() -> None:
    created = client.post("/api/characters", json={"name": "Evolver"}).json()
    minutes_to_level_10 = character_router.LEVEL_THRESHOLDS[9]

    response = client.post(
        f"/api/characters/{created['id']}/study",
        json={"minutes": minutes_to_level_10},
    )

    assert response.status_code == 200
    assert response.json()["level"] == 10
    assert response.json()["highest_level"] == 10
    assert response.json()["evolution_stage"] == 1


def test_penalty_never_drops_below_highest_level_minus_ten() -> None:
    minutes_to_level_30 = character_router.LEVEL_THRESHOLDS[29]
    character = make_character(total_study_minutes=minutes_to_level_30)
    character_router.refresh_character_progress(character)

    assert character.level == 30
    assert character.highest_level == 30
    assert character.minimum_level == 20

    for _ in range(500):
        character_router.apply_one_penalty(character)

    assert character.level == 20
    assert character.highest_level == 30
    assert character.minimum_level == 20
    assert character_router.apply_one_penalty(character) == 0


def test_inactivity_penalty_counts_only_dates_between_study_days(monkeypatch) -> None:
    last_study = datetime(2026, 9, 12, 12, tzinfo=character_router.STUDY_TIMEZONE)
    current_study = datetime(2026, 9, 15, 12, tzinfo=character_router.STUDY_TIMEZONE)
    character = make_character(
        last_studied_at=last_study,
        penalty_applied_through=date(2026, 9, 12),
    )
    applied_count = 0

    def count_penalty(_: Character) -> int:
        nonlocal applied_count
        applied_count += 1
        return 0

    monkeypatch.setattr(character_router, "apply_one_penalty", count_penalty)

    character_router.apply_inactivity_penalty(character, current_study)

    assert applied_count == 2
    assert character.penalty_applied_through == date(2026, 9, 14)


def test_format_minutes_supports_more_than_24_hours() -> None:
    assert character_router.format_minutes(1_505) == "25:05"
