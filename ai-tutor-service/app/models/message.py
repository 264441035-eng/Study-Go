from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, Field


class Role(str, Enum):
    user = "user"
    assistant = "assistant"


class ConversationMessage(BaseModel):
    session_id: str
    role: Role
    content: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
