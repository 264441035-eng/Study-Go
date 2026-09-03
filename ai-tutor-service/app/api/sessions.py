"""Session API (計画 §4 / 仕様書12章)。

POST /sessions                     … 開始 + 最初の質問
POST /sessions/{id}/messages       … 回答送信 → 次の質問 + state
POST /sessions/{id}/finish         … 終了 (Assessment/Report は後続PRで実装)
すべて JWT 必須。user_id は JWT から取得しボディの user_id は使わない。
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import (
    get_assessment_service,
    get_conversation_service,
    get_report_service,
    get_session_repo,
    get_student_model_service,
)
from app.auth import get_current_user_id
from app.config import Settings, get_settings
from app.models import ConversationMessage, Role, Session, SessionStatus
from app.models.api import (
    FinishResponse,
    SendMessageRequest,
    SendMessageResponse,
    StartSessionRequest,
    StartSessionResponse,
)
from app.repositories import SessionRepository
from app.services import limits
from app.services.assessment import DEFAULT_SUBJECT, AssessmentService
from app.services.conversation import ConversationService
from app.services.report import ReportService
from app.services.student_model import StudentModelService

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
    body: StartSessionRequest | None = None,
    user_id: str = Depends(get_current_user_id),
    repo: SessionRepository = Depends(get_session_repo),
    conv: ConversationService = Depends(get_conversation_service),
    settings: Settings = Depends(get_settings),
) -> StartSessionResponse:
    limits.check_daily_session_limit(user_id, repo, settings)
    persona = body.persona if body else None
    session = Session(user_id=user_id, persona=persona)
    repo.create_session(session)
    opening = conv.opening_message(persona)
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
    session = _load_owned_active_session(repo, session_id, user_id)
    limits.check_message_length(body.message, settings)

    repo.add_message(
        ConversationMessage(session_id=session_id, role=Role.user, content=body.message)
    )
    history = repo.get_messages(session_id)
    text, state = conv.next_message(history, session)
    repo.add_message(
        ConversationMessage(session_id=session_id, role=Role.assistant, content=text)
    )
    return SendMessageResponse(message=text, state=state)


@router.post("/{session_id}/finish", response_model=FinishResponse)
def finish_session(
    session_id: str,
    user_id: str = Depends(get_current_user_id),
    repo: SessionRepository = Depends(get_session_repo),
    assessor: AssessmentService = Depends(get_assessment_service),
    student: StudentModelService = Depends(get_student_model_service),
    reporter: ReportService = Depends(get_report_service),
) -> FinishResponse:
    session = _load_owned_active_session(repo, session_id, user_id)
    history = repo.get_messages(session_id)

    assessment = assessor.assess(session, history)
    repo.save_assessment(assessment)
    student.apply(user_id, session.subject or DEFAULT_SUBJECT, assessment)
    report = reporter.build(session, assessment)

    # finish は一度きり。二重 finish は _load_owned_active_session が 409 で弾く。
    session.status = SessionStatus.finished
    session.finished_at = datetime.now(timezone.utc)
    repo.update_session(session)

    return FinishResponse(
        session_id=session_id,
        score=assessment.overall_score,
        summary=report.comment,
        strengths=assessment.strengths,
        weaknesses=assessment.weaknesses,
        xp=report.xp,
    )
