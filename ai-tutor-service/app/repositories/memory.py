"""in-memory 実装 (DATABASE_MODE=memory)。

開発・テスト用。プロセス内に保持するだけで永続化しない。
本番用 DynamoDB 実装は後続PRで追加する。
"""

from datetime import date

from app.models import Assessment, ConversationMessage, Session
from app.repositories.interface import SessionRepository, StudentModelRepository


class InMemorySessionRepository(SessionRepository):
    def __init__(self) -> None:
        self._sessions: dict[str, Session] = {}
        self._messages: dict[str, list[ConversationMessage]] = {}
        self._assessments: dict[str, Assessment] = {}

    def create_session(self, session: Session) -> None:
        self._sessions[session.session_id] = session
        self._messages.setdefault(session.session_id, [])

    def get_session(self, session_id: str) -> Session | None:
        return self._sessions.get(session_id)

    def update_session(self, session: Session) -> None:
        self._sessions[session.session_id] = session

    def add_message(self, message: ConversationMessage) -> None:
        self._messages.setdefault(message.session_id, []).append(message)

    def get_messages(self, session_id: str) -> list[ConversationMessage]:
        return list(self._messages.get(session_id, []))

    def save_assessment(self, assessment: Assessment) -> None:
        self._assessments[assessment.session_id] = assessment

    def get_assessment(self, session_id: str) -> Assessment | None:
        return self._assessments.get(session_id)

    def count_user_sessions_on(self, user_id: str, on: date) -> int:
        return sum(
            1
            for s in self._sessions.values()
            if s.user_id == user_id and s.created_at.date() == on
        )


class InMemoryStudentModelRepository(StudentModelRepository):
    def __init__(self) -> None:
        # (user_id, subject, topic) -> dict
        self._store: dict[tuple[str, str, str], dict] = {}

    def upsert_topic(
        self,
        user_id: str,
        subject: str,
        topic: str,
        *,
        score: int,
        confidence: float,
        weaknesses: list[str],
        last_assessed_at: str,
    ) -> None:
        self._store[(user_id, subject, topic)] = {
            "score": score,
            "confidence": confidence,
            "weaknesses": weaknesses,
            "last_assessed_at": last_assessed_at,
        }

    def get_topic(self, user_id: str, subject: str, topic: str) -> dict | None:
        return self._store.get((user_id, subject, topic))
