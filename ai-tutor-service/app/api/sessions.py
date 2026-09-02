"""Session API (計画 §4 / 仕様書12章)。

POST /sessions                     … 開始 + 最初の質問
POST /sessions/{id}/messages       … 回答送信 → 次の質問 + state
POST /sessions/{id}/finish         … 終了 (Assessment/Report は後続PRで実装)
すべて JWT 必須。user_id は JWT から取得しボディの user_id は使わない。
"""

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_conversation_service, get_session_repo
from app.auth import get_current_user_id
from app.config import Settings, get_settings
from app.models import ConversationMessage, Role, Session, SessionStatus
from app.models.api import (
    SendMessageRequest,
    SendMessageResponse,
    StartSessionResponse,
)
from app.repositories import SessionRepository
from app.services import limits
from app.services.conversation import ConversationService

router = APIRouter(prefix="/sessions", tags=["sessions"])


def _load_owned_active_session(
    repo: SessionRepository, session_id: str, user_id: str
) -> Session:
    session = repo.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="session not found")
    if session.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="not your session")
    if session.status is not SessionStatus.active:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="session already finished"
        )
    return session


@router.post("", response_model=StartSessionResponse)
def start_session(
    user_id: str = Depends(get_current_user_id),
    repo: SessionRepository = Depends(get_session_repo),
    conv: ConversationService = Depends(get_conversation_service),
    settings: Settings = Depends(get_settings),
) -> StartSessionResponse:
    limits.check_daily_session_limit(user_id, repo, settings)
    session = Session(user_id=user_id)
    repo.create_session(session)
    opening = conv.opening_message()
    repo.add_message(
        ConversationMessage(
            session_id=session.session_id, role=Role.assistant, content=opening
        )
    )
    return StartSessionResponse(session_id=session.session_id, message=opening)


@router.post("/{session_id}/messages", response_model=SendMessageResponse)
def send_message(
    session_id: str,
    body: SendMessageRequest,
    user_id: str = Depends(get_current_user_id),
    repo: SessionRepository = Depends(get_session_repo),
    conv: ConversationService = Depends(get_conversation_service),
    settings: Settings = Depends(get_settings),
) -> SendMessageResponse:
    _load_owned_active_session(repo, session_id, user_id)
    limits.check_message_length(body.message, settings)

    repo.add_message(
        ConversationMessage(session_id=session_id, role=Role.user, content=body.message)
    )
    history = repo.get_messages(session_id)
    text, state = conv.next_message(history)
    repo.add_message(
        ConversationMessage(session_id=session_id, role=Role.assistant, content=text)
    )
    return SendMessageResponse(message=text, state=state)
