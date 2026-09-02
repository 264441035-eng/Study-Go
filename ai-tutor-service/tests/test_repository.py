from datetime import date


from app.config import DatabaseMode, Settings
from app.models import Assessment, ConversationMessage, Role, Session
from app.repositories import get_session_repository
from app.repositories.factory import get_student_model_repository
from app.repositories.memory import (
    InMemorySessionRepository,
    InMemoryStudentModelRepository,
)


def test_session_crud_and_messages():
    repo = InMemorySessionRepository()
    s = Session(user_id="u1")
    repo.create_session(s)
    assert repo.get_session(s.session_id).user_id == "u1"

    repo.add_message(ConversationMessage(session_id=s.session_id, role=Role.assistant, content="q1"))
    repo.add_message(ConversationMessage(session_id=s.session_id, role=Role.user, content="a1"))
    msgs = repo.get_messages(s.session_id)
    assert [m.content for m in msgs] == ["q1", "a1"]


def test_assessment_save_get():
    repo = InMemorySessionRepository()
    s = Session(user_id="u1")
    repo.create_session(s)
    a = Assessment(session_id=s.session_id, topic="quadratic_functions", overall_score=72)
    repo.save_assessment(a)
    assert repo.get_assessment(s.session_id).overall_score == 72


def test_count_user_sessions_on():
    repo = InMemorySessionRepository()
    repo.create_session(Session(user_id="u1"))
    repo.create_session(Session(user_id="u1"))
    repo.create_session(Session(user_id="u2"))
    assert repo.count_user_sessions_on("u1", date.today()) == 2
    assert repo.count_user_sessions_on("u2", date.today()) == 1


def test_student_model_upsert_get():
    repo = InMemoryStudentModelRepository()
    repo.upsert_topic(
        "u1", "math", "quadratic_functions",
        score=72, confidence=0.84, weaknesses=["completing_the_square"],
        last_assessed_at="2026-09-02T10:00:00Z",
    )
    got = repo.get_topic("u1", "math", "quadratic_functions")
    assert got["score"] == 72
    assert repo.get_topic("u1", "math", "unknown") is None


def test_factory_selects_impl_by_mode():
    from app.repositories.dynamodb import (
        DynamoDBSessionRepository,
        DynamoDBStudentModelRepository,
    )

    assert get_session_repository(Settings(database_mode=DatabaseMode.memory)) is not None
    # DynamoDB 実装の選択 (boto3 resource 生成のみ; ネットワークアクセスはしない)。
    assert isinstance(
        get_session_repository(Settings(database_mode=DatabaseMode.aws)),
        DynamoDBSessionRepository,
    )
    assert isinstance(
        get_student_model_repository(Settings(database_mode=DatabaseMode.local)),
        DynamoDBStudentModelRepository,
    )
