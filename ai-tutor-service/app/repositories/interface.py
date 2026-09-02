"""永続化の抽象 (計画 §1-⑤)。

DATABASE_MODE で実装を差し替える。in-memory で先行実装し、後続PRで
DynamoDB (Sessions / StudentModels 2テーブル) に差し替える。
"""

from abc import ABC, abstractmethod
from datetime import date

from app.models import Assessment, ConversationMessage, Session


class SessionRepository(ABC):
    @abstractmethod
    def create_session(self, session: Session) -> None: ...

    @abstractmethod
    def get_session(self, session_id: str) -> Session | None: ...

    @abstractmethod
    def update_session(self, session: Session) -> None: ...

    @abstractmethod
    def add_message(self, message: ConversationMessage) -> None: ...

    @abstractmethod
    def get_messages(self, session_id: str) -> list[ConversationMessage]:
        """時系列順で返す。"""

    @abstractmethod
    def save_assessment(self, assessment: Assessment) -> None: ...

    @abstractmethod
    def get_assessment(self, session_id: str) -> Assessment | None: ...

    @abstractmethod
    def count_user_sessions_on(self, user_id: str, on: date) -> int:
        """指定日に user が開始したセッション数 (日次上限の判定用)。"""


class StudentModelRepository(ABC):
    @abstractmethod
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
    ) -> None: ...

    @abstractmethod
    def get_topic(self, user_id: str, subject: str, topic: str) -> dict | None: ...
