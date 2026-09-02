"""アプリ設定と依存モードの切替。

環境変数で依存を差し替えられるようにする（Phase1計画 §5 / 仕様書15章）。
  LLM_MODE      = mock | bedrock
  BACKEND_MODE  = mock | real
  DATABASE_MODE = memory | local | aws
  RAG_MODE      = mock | bedrock   (Phase1 は mock 固定; Bedrock KB は Phase2)
"""

from enum import Enum
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class LLMMode(str, Enum):
    mock = "mock"
    bedrock = "bedrock"


class BackendMode(str, Enum):
    mock = "mock"
    real = "real"


class DatabaseMode(str, Enum):
    memory = "memory"
    local = "local"
    aws = "aws"


class RAGMode(str, Enum):
    mock = "mock"
    bedrock = "bedrock"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    app_env: str = "local"

    # --- 依存モード ---
    llm_mode: LLMMode = LLMMode.mock
    backend_mode: BackendMode = BackendMode.mock
    database_mode: DatabaseMode = DatabaseMode.memory
    rag_mode: RAGMode = RAGMode.mock

    # --- Bedrock (LLM_MODE=bedrock のとき使用) ---
    # ap-northeast-1 で疎通確認済み (計画 §1-③)。組織の SCP が global.* /
    # Sonnet 5 を explicit deny するため jp.* Inference Profile を pin。
    bedrock_region: str = "ap-northeast-1"
    conversation_model_id: str = "jp.anthropic.claude-haiku-4-5-20251001-v1:0"
    assessment_model_id: str = "jp.anthropic.claude-sonnet-4-5-20250929-v1:0"

    # --- 認証 (JWT HS256, 既存backendと共有シークレット; 計画 §1-①) ---
    jwt_secret: str = "dev-insecure-secret-change-me"
    jwt_algorithm: str = "HS256"

    # --- 既存 Backend (BACKEND_MODE=real のとき使用) ---
    existing_backend_base_url: str = "http://localhost:8080"

    # --- DynamoDB (DATABASE_MODE=local|aws のとき使用) ---
    # local は DynamoDB Local の endpoint を指す。aws は None のまま。
    dynamodb_endpoint_url: str | None = None
    sessions_table: str = "ai-tutor-sessions"
    student_models_table: str = "ai-tutor-student-models"

    # --- コストの蓋 (計画 §1-③) ---
    max_turns: int = 10
    max_sessions_per_day: int = 20
    max_message_chars: int = 2000

    # --- CORS ---
    cors_origins: str = "http://localhost:3000,http://localhost:5173"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
