"""DATABASE_MODE に応じて Repository 実装を選ぶ。

memory 実装はプロセス内でリクエストをまたいで状態を保つためシングルトン。
local/aws (DynamoDB) は後続PRで実装する。
"""

from functools import lru_cache

from app.config import DatabaseMode, Settings
from app.repositories.interface import SessionRepository, StudentModelRepository


@lru_cache
def _memory_session_repo() -> SessionRepository:
    from app.repositories.memory import InMemorySessionRepository

    return InMemorySessionRepository()


@lru_cache
def _memory_student_repo() -> StudentModelRepository:
    from app.repositories.memory import InMemoryStudentModelRepository

    return InMemoryStudentModelRepository()


def get_session_repository(settings: Settings) -> SessionRepository:
    if settings.database_mode is DatabaseMode.memory:
        return _memory_session_repo()
    raise NotImplementedError(
        f"DynamoDB session repository ({settings.database_mode}) is added in a later PR"
    )


def get_student_model_repository(settings: Settings) -> StudentModelRepository:
    if settings.database_mode is DatabaseMode.memory:
        return _memory_student_repo()
    raise NotImplementedError(
        f"DynamoDB student-model repository ({settings.database_mode}) is added in a later PR"
    )
