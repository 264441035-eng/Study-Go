import uuid
from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, Field


class SessionStatus(str, Enum):
    active = "active"
    finished = "finished"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _new_session_id() -> str:
    return "session_" + uuid.uuid4().hex[:12]


class Session(BaseModel):
    session_id: str = Field(default_factory=_new_session_id)
    user_id: str
    status: SessionStatus = SessionStatus.active

    subject: str | None = None
    topic: str | None = None
    concept_index: int = 0

    created_at: datetime = Field(default_factory=_now)
    finished_at: datetime | None = None