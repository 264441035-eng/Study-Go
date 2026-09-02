"""API 層の依存注入プロバイダ。"""

from fastapi import Depends

from app.config import Settings, get_settings
from app.llm import get_llm_client
from app.llm.interface import LLMClient
from app.repositories import (
    SessionRepository,
    StudentModelRepository,
    get_session_repository,
    get_student_model_repository,
)
from app.services.assessment import AssessmentService
from app.services.conversation import ConversationService
from app.services.report import ReportService
from app.services.student_model import StudentModelService


def get_llm(settings: Settings = Depends(get_settings)) -> LLMClient:
    return get_llm_client(settings)


def get_session_repo(settings: Settings = Depends(get_settings)) -> SessionRepository:
    return get_session_repository(settings)


def get_student_repo(
    settings: Settings = Depends(get_settings),
) -> StudentModelRepository:
    return get_student_model_repository(settings)


def get_conversation_service(
    llm: LLMClient = Depends(get_llm),
    settings: Settings = Depends(get_settings),
) -> ConversationService:
    return ConversationService(llm, settings)


def get_assessment_service(
    llm: LLMClient = Depends(get_llm),
    settings: Settings = Depends(get_settings),
) -> AssessmentService:
    return AssessmentService(llm, settings)


def get_student_model_service(
    repo: StudentModelRepository = Depends(get_student_repo),
) -> StudentModelService:
    return StudentModelService(repo)


def get_report_service() -> ReportService:
    return ReportService()
