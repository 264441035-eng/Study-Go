from fastapi.testclient import TestClient

from app.main import app
from app.routers import task as task_router

client = TestClient(app)


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