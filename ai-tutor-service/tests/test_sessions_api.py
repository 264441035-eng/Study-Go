import pytest
from fastapi.testclient import TestClient

from app.auth import create_access_token
from app.config import Settings, get_settings
from app.main import app
from app.repositories import factory

client = TestClient(app)

TOKEN = create_access_token("user123", get_settings())
HEADERS = {"Authorization": f"Bearer {TOKEN}"}


@pytest.fixture(autouse=True)
def _fresh_repos():
    # in-memory repo はシングルトンなのでテストごとに作り直す。
    factory._memory_session_repo.cache_clear()
    factory._memory_student_repo.cache_clear()
    yield
    app.dependency_overrides.clear()


def _start() -> str:
    resp = client.post("/sessions", headers=HEADERS)
    assert resp.status_code == 200
    return resp.json()["session_id"]


def test_start_requires_auth():
    assert client.post("/sessions").status_code == 401


def test_start_returns_opening_question():
    resp = client.post("/sessions", headers=HEADERS)
    assert resp.status_code == 200
    body = resp.json()
    assert body["session_id"].startswith("session_")
    assert "何を勉強" in body["message"]


def test_message_flow_and_state_progression():
    sid = _start()
    states = []
    for text in ["二次関数", "平方完成のこと", "頂点を求めるため", "式変形だから"]:
        resp = client.post(
            f"/sessions/{sid}/messages", headers=HEADERS, json={"message": text}
        )
        assert resp.status_code == 200
        body = resp.json()
        assert set(body.keys()) == {"message", "state"}  # tool内部は返さない
        states.append(body["state"])
    # 序盤は questioning、下限を超えたら ready_to_finish
    assert states[0] == "questioning"
    assert states[-1] == "ready_to_finish"


def test_message_length_limit():
    sid = _start()
    app.dependency_overrides[get_settings] = lambda: Settings(max_message_chars=5)
    resp = client.post(
        f"/sessions/{sid}/messages", headers=HEADERS, json={"message": "123456"}
    )
    assert resp.status_code == 413


def test_daily_session_limit():
    app.dependency_overrides[get_settings] = lambda: Settings(max_sessions_per_day=1)
    assert client.post("/sessions", headers=HEADERS).status_code == 200
    assert client.post("/sessions", headers=HEADERS).status_code == 429


def test_message_to_unknown_session_404():
    resp = client.post(
        "/sessions/session_nope/messages", headers=HEADERS, json={"message": "hi"}
    )
    assert resp.status_code == 404


def test_cannot_use_others_session():
    sid = _start()
    other = create_access_token("intruder", get_settings())
    resp = client.post(
        f"/sessions/{sid}/messages",
        headers={"Authorization": f"Bearer {other}"},
        json={"message": "hi"},
    )
    assert resp.status_code == 403


def test_finish_returns_assessment_and_report():
    sid = _start()
    client.post(f"/sessions/{sid}/messages", headers=HEADERS, json={"message": "二次関数"})
    resp = client.post(f"/sessions/{sid}/finish", headers=HEADERS)
    assert resp.status_code == 200
    body = resp.json()
    assert body["session_id"] == sid
    assert set(body.keys()) == {"session_id", "score", "summary", "strengths", "weaknesses", "xp"}
    assert 0 <= body["score"] <= 100
    assert body["xp"] >= 0
    assert body["strengths"] and body["summary"]


def test_finish_summary_is_natural_japanese():
    sid = _start()
    client.post(f"/sessions/{sid}/messages", headers=HEADERS, json={"message": "二次関数"})
    resp = client.post(f"/sessions/{sid}/finish", headers=HEADERS)
    assert resp.status_code == 200
    body = resp.json()
    assert "review_vertex_form" not in body["summary"]
    assert "平方完成と頂点形式の関係" in body["summary"]


def test_finish_persists_assessment_and_student_model():
    sid = _start()
    client.post(f"/sessions/{sid}/finish", headers=HEADERS)
    session_repo = factory.get_session_repository(get_settings())
    student_repo = factory.get_student_model_repository(get_settings())
    assert session_repo.get_assessment(sid) is not None
    # Student Model に該当 topic が upsert されている (mock は quadratic_functions)。
    topic = student_repo.get_topic("user123", "math", "quadratic_functions")
    assert topic is not None
    assert 0 <= topic["score"] <= 100


def test_finish_is_idempotent_second_call_409():
    sid = _start()
    assert client.post(f"/sessions/{sid}/finish", headers=HEADERS).status_code == 200
    # 二度目は finished なので 409。
    assert client.post(f"/sessions/{sid}/finish", headers=HEADERS).status_code == 409


def test_cannot_message_after_finish():
    sid = _start()
    client.post(f"/sessions/{sid}/finish", headers=HEADERS)
    resp = client.post(f"/sessions/{sid}/messages", headers=HEADERS, json={"message": "hi"})
    assert resp.status_code == 409


def test_finish_requires_auth():
    sid = _start()
    assert client.post(f"/sessions/{sid}/finish").status_code == 401
