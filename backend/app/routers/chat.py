"""チャット(chat)機能に関するエンドポイント。

新しい機能を追加するときは、この routers/ 配下に
このファイルのような <機能名>.py を作成し、
main.py で `app.include_router(...)` を1行追加するだけで良い。
"""

import os

import httpx
from fastapi import APIRouter, Body, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

router = APIRouter(prefix="/api/chat", tags=["chat"])

# ai-tutor-service のベース URL。本番では Terraform 側で backend タスクの
# 環境変数として設定する（未設定時はローカル docker-compose を想定した既定値）。
AI_TUTOR_SERVICE_URL = os.getenv("AI_TUTOR_SERVICE_URL", "http://localhost:8000")

# 上流(ai-tutor-service)呼び出しのタイムアウト秒。LLM 応答を待つので長めにとる。
_AI_TUTOR_TIMEOUT = 30.0


class ChatMessage(BaseModel):
    sender: str
    content: str


class ChatMessageOut(ChatMessage):
    id: int


# TODO: 現状はメモリ上に保持するだけの仮実装。
# DBを導入したら SQLAlchemy 等のリポジトリ層に置き換える。
_messages: list[ChatMessageOut] = []
_next_id = 1


@router.get("")
def list_messages() -> list[ChatMessageOut]:
    return _messages


@router.post("", status_code=201)
def create_message(message: ChatMessage) -> ChatMessageOut:
    global _next_id
    created = ChatMessageOut(id=_next_id, **message.model_dump())
    _messages.append(created)
    _next_id += 1
    return created


# ---- AI Tutor プロキシ ----
# frontend は自前バックエンド経由で ai-tutor-service を呼ぶ (frontend/src/aiTutor.ts)。
# ここで /api/chat/sessions* を ai-tutor-service の /sessions* へ中継する。
# JWT (Authorization ヘッダ) はそのまま上流へ渡す（認可は ai-tutor-service 側で行う）。
def _proxy_to_ai_tutor(request: Request, path: str, body: dict | None) -> JSONResponse:
    headers: dict[str, str] = {}
    authorization = request.headers.get("authorization")
    if authorization:
        headers["Authorization"] = authorization

    with httpx.Client(base_url=AI_TUTOR_SERVICE_URL, timeout=_AI_TUTOR_TIMEOUT) as client:
        upstream = client.request(request.method, path, headers=headers, json=body)

    return JSONResponse(status_code=upstream.status_code, content=upstream.json())


@router.post("/sessions")
def start_ai_tutor_session(request: Request) -> JSONResponse:
    return _proxy_to_ai_tutor(request, "/sessions", None)


@router.post("/sessions/{session_id}/messages")
def send_ai_tutor_message(
    session_id: str, request: Request, body: dict = Body(...)
) -> JSONResponse:
    return _proxy_to_ai_tutor(request, f"/sessions/{session_id}/messages", body)


@router.post("/sessions/{session_id}/finish")
def finish_ai_tutor_session(session_id: str, request: Request) -> JSONResponse:
    return _proxy_to_ai_tutor(request, f"/sessions/{session_id}/finish", None)
