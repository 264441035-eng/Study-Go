"""チャット(chat)機能に関するエンドポイント。

新しい機能を追加するときは、この routers/ 配下に
このファイルのような <機能名>.py を作成し、
main.py で `app.include_router(...)` を1行追加するだけで良い。
"""

import os

import httpx
from fastapi import APIRouter, Body, Depends, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.routers.character import (
    add_study_minutes_to_character,
    get_or_create_demo_character,
    utc_now,
)

router = APIRouter(prefix="/api/chat", tags=["chat"])

# ai-tutor-service のベース URL。本番では Terraform 側で backend タスクの
# 環境変数として設定する（未設定時はローカル docker-compose を想定した既定値）。
AI_TUTOR_SERVICE_URL = os.getenv("AI_TUTOR_SERVICE_URL", "http://localhost:8000")

# 上流(ai-tutor-service)呼び出しのタイムアウト秒。LLM 応答を待つので長めにとる。
_AI_TUTOR_TIMEOUT = 30.0

# チャット完了で得た xp を、キャラの経験値（分換算）へ変換するときの除数。
# ai-tutor の xp は概ね 0〜80 のため、そのまま分にすると進化が速すぎる。
# デモの均衡用に小さめの分数へ丸める。本番では環境変数で調整する。
CHAT_FINISH_XP_DIVISOR = int(os.getenv("CHAT_FINISH_XP_DIVISOR", "10"))


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
def _call_ai_tutor(
    request: Request, path: str, body: dict | None
) -> tuple[int, object]:
    """ai-tutor-service を呼び出し、(ステータスコード, JSONボディ) を返す。"""
    headers: dict[str, str] = {}
    authorization = request.headers.get("authorization")
    if authorization:
        headers["Authorization"] = authorization

    with httpx.Client(base_url=AI_TUTOR_SERVICE_URL, timeout=_AI_TUTOR_TIMEOUT) as client:
        upstream = client.request(request.method, path, headers=headers, json=body)

    return upstream.status_code, upstream.json()


def _proxy_to_ai_tutor(request: Request, path: str, body: dict | None) -> JSONResponse:
    status_code, content = _call_ai_tutor(request, path, body)
    return JSONResponse(status_code=status_code, content=content)


def _apply_chat_finish_xp(content: object, db: Session) -> dict | None:
    """チャット完了レスポンスの xp をキャラの経験値（分換算）として加算する。

    ログインのないデモではDBの先頭の1体（なければ作成）へ加算する。
    xp が取れない・0以下・変換後0分の場合は何もしない（None を返す）。

    加算できた場合は、フロントが「経験値が増えた」ことを通知できるよう、
    実際に付与した分数・加算後のレベル・レベルアップ有無・進化段階を返す。
    """
    if not isinstance(content, dict):
        return None

    xp = content.get("xp")
    if not isinstance(xp, (int, float)) or xp <= 0:
        return None

    divisor = CHAT_FINISH_XP_DIVISOR if CHAT_FINISH_XP_DIVISOR > 0 else 1
    minutes = round(xp / divisor)
    if minutes <= 0:
        return None

    character = get_or_create_demo_character(db, for_update=True)
    level_before = character.level
    add_study_minutes_to_character(character, minutes, utc_now())
    db.commit()

    return {
        "awarded_xp_minutes": minutes,
        "character_level": character.level,
        "leveled_up": character.level > level_before,
        "evolution_stage": character.evolution_stage,
    }


@router.post("/dev/token")
def issue_dev_token(request: Request, body: dict = Body(...)) -> JSONResponse:
    """開発用トークン払い出しを ai-tutor-service の /dev/token へ中継する。

    ai-tutor-service が APP_ENV=local のときだけ有効。それ以外は上流が404を返し、
    フロントはログイン画面／配布URLのトークンにフォールバックする。
    """
    return _proxy_to_ai_tutor(request, "/dev/token", body)


@router.post("/sessions")
def start_ai_tutor_session(request: Request) -> JSONResponse:
    return _proxy_to_ai_tutor(request, "/sessions", None)


@router.post("/sessions/{session_id}/messages")
def send_ai_tutor_message(
    session_id: str, request: Request, body: dict = Body(...)
) -> JSONResponse:
    return _proxy_to_ai_tutor(request, f"/sessions/{session_id}/messages", body)


@router.post("/sessions/{session_id}/finish")
def finish_ai_tutor_session(
    session_id: str, request: Request, db: Session = Depends(get_db)
) -> JSONResponse:
    status_code, content = _call_ai_tutor(
        request, f"/sessions/{session_id}/finish", None
    )
    # 完了に成功したときだけ、得た xp をキャラの経験値へ反映する。
    # 付与できたら、フロントが通知に使えるよう獲得分数・レベル情報を応答へ足す。
    if status_code == 200:
        awarded = _apply_chat_finish_xp(content, db)
        if awarded and isinstance(content, dict):
            content = {**content, **awarded}
    return JSONResponse(status_code=status_code, content=content)
