"""AI Tutor Service エントリポイント。"""

import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import dev, sessions
from app.config import DatabaseMode, get_settings

logger = logging.getLogger("ai_tutor")
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # local (DynamoDB Local) はテーブルを自動作成する。aws は Terraform 管理なので触らない。
    if settings.database_mode is DatabaseMode.local:
        from app.repositories.dynamodb import ensure_tables

        last_err: Exception | None = None
        for _ in range(15):
            try:
                ensure_tables(settings)
                logger.info("DynamoDB Local tables ready")
                break
            except Exception as e:  # noqa: BLE001 - 起動待ちをリトライ
                last_err = e
                time.sleep(1)
        else:
            raise RuntimeError(f"could not ensure DynamoDB tables: {last_err}")
    yield


app = FastAPI(title="AI Tutor Service", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(sessions.router)
app.include_router(dev.router)


@app.get("/health")
def health() -> dict:
    """ヘルスチェック。起動中の依存モードも返す（スモークテスト用）。"""
    return {
        "status": "ok",
        "modes": {
            "app_env": settings.app_env,
            "llm": settings.llm_mode.value,
            "backend": settings.backend_mode.value,
            "database": settings.database_mode.value,
            "rag": settings.rag_mode.value,
        },
    }
