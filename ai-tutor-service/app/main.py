"""AI Tutor Service エントリポイント。

Phase1 skeleton: FastAPI アプリと /health のみ。
Session API・Conversation・Assessment 等は後続の stacked PR で追加する。
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings

settings = get_settings()

app = FastAPI(title="AI Tutor Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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
