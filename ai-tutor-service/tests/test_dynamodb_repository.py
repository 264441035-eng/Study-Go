"""DynamoDB Repository のテスト (moto で実DynamoDBを模擬)。

memory 実装と同じ契約を満たすことを検証する (計画 acceptance #6)。
"""

from datetime import date, datetime, timezone

import pytest
from moto import mock_aws

from app.config import DatabaseMode, Settings
from app.models import Assessment, ConversationMessage, Role, Session, SubtopicScore


@pytest.fixture
def settings() -> Settings:
    return Settings(
        database_mode=DatabaseMode.aws,
        bedrock_region="us-east-1",
        sessions_table="test-sessions",
        student_models_table="test-student-models",
    )


@pytest.fixture
def repos(settings):
    from app.repositories import dynamodb

    with mock_aws():
        # lru_cache された boto3 resource がテスト間で漏れないようにする。
        dynamodb._resource.cache_clear()
        dynamodb.ensure_tables(settings)
        yield (
            dynamodb.DynamoDBSessionRepository(settings),
            dynamodb.DynamoDBStudentModelRepository(settings),
        )
        dynamodb._resource.cache_clear()


def test_session_roundtrip(repos):
    session_repo, _ = repos
    session = Session(user_id="u1", subject="math")
    session_repo.create_session(session)

    loaded = session_repo.get_session(session.session_id)
    assert loaded is not None
    assert loaded.user_id == "u1"
    assert loaded.subject == "math"


def test_unknown_session_returns_none(repos):
    session_repo, _ = repos
    assert session_repo.get_session("session_missing") is None


def test_messages_are_ordered(repos):
    session_repo, _ = repos
    sid = "session_msgs"
    for i, role in enumerate([Role.assistant, Role.user, Role.assistant]):
        session_repo.add_message(
            ConversationMessage(session_id=sid, role=role, content=f"m{i}")
        )
    msgs = session_repo.get_messages(sid)
    assert [m.content for m in msgs] == ["m0", "m1", "m2"]


def test_assessment_roundtrip(repos):
    session_repo, _ = repos
    sid = "session_assess"
    assessment = Assessment(
        session_id=sid,
        topic="quadratic_functions",
        subtopics=[SubtopicScore(name="completing_the_square", score=72, confidence=0.8)],
        overall_score=72,
        strengths=["ok"],
        weaknesses=["hmm"],
        recommended_next_action="review",
    )
    session_repo.save_assessment(assessment)
    loaded = session_repo.get_assessment(sid)
    assert loaded is not None
    assert loaded.overall_score == 72
    assert loaded.subtopics[0].confidence == 0.8


def test_daily_session_count_via_gsi(repos):
    session_repo, _ = repos
    today = datetime.now(timezone.utc)
    for _ in range(3):
        session_repo.create_session(Session(user_id="counter", created_at=today))
    # 別ユーザー / 別日はカウントされない。
    session_repo.create_session(Session(user_id="other", created_at=today))

    assert session_repo.count_user_sessions_on("counter", today.date()) == 3
    assert session_repo.count_user_sessions_on("counter", date(2000, 1, 1)) == 0


def test_student_model_upsert_and_get(repos):
    _, student_repo = repos
    student_repo.upsert_topic(
        "u1",
        "math",
        "quadratic_functions",
        score=72,
        confidence=0.8,
        weaknesses=["vertex"],
        last_assessed_at="2026-09-02T00:00:00+00:00",
    )
    topic = student_repo.get_topic("u1", "math", "quadratic_functions")
    assert topic == {
        "score": 72,
        "confidence": 0.8,
        "weaknesses": ["vertex"],
        "last_assessed_at": "2026-09-02T00:00:00+00:00",
    }
    assert student_repo.get_topic("u1", "math", "unknown") is None
