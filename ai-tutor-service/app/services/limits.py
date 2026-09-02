"""コストの蓋 (計画 §1-③)。

会話ターン上限は ConversationService 側、ここでは入力長と日次セッション数を守る。
"""

from datetime import date, datetime, timezone

from fastapi import HTTPException, status

from app.config import Settings
from app.repositories.interface import SessionRepository


def _utc_today() -> date:
    return datetime.now(timezone.utc).date()


def check_message_length(message: str, settings: Settings) -> None:
    if len(message) > settings.max_message_chars:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"message exceeds {settings.max_message_chars} characters",
        )


def check_daily_session_limit(
    user_id: str, repo: SessionRepository, settings: Settings
) -> None:
    # session.created_at は UTC なので UTC 日付で数える。
    if repo.count_user_sessions_on(user_id, _utc_today()) >= settings.max_sessions_per_day:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="daily session limit reached",
        )
