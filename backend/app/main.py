import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import base, character, chat, encounter, task

app = FastAPI(title="Study-Go API")

# フロントエンドのオリジンを環境変数で許可（カンマ区切り）
_default_origins = (
    "http://localhost:5173,http://localhost:5174,http://localhost:5175,"
    "http://localhost:3000"
)
_origins = os.getenv("CORS_ORIGINS", _default_origins)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in _origins.split(",") if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    """ALB / ECS のヘルスチェック用エンドポイント。"""
    return {"status": "ok"}


@app.get("/api/hello")
def hello() -> dict[str, str]:
    return {"message": "Hello from FastAPI on ECS Fargate"}


# 新機能は app/routers/ 配下にファイルを追加し、ここで include_router するだけでよい。
app.include_router(base.router)
app.include_router(character.router)
app.include_router(chat.router)
app.include_router(encounter.router)
app.include_router(task.router)


