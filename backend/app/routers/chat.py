"""
チャット(chat)機能に関するエンドポイント。

現在はモックとして動作する。
将来的にAmazon Bedrockを利用したAIチャットへ置き換える。
"""

from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.services.chat_service import (
    generate_feedback,
    generate_question,
    generate_reply,
)


router = APIRouter(
    prefix="/api/chat",
    tags=["chat"],
)


# ============================================================
# Request / Response Models
# ============================================================


class MessageRequest(BaseModel):
    """ユーザーからの通常メッセージ。"""

    message: str = Field(
        min_length=1,
        max_length=1000,
    )


class ExplanationRequest(BaseModel):
    """ユーザーによる学習内容の説明。"""

    explanation: str = Field(
        min_length=1,
        max_length=3000,
    )


class TodayContentRequest(BaseModel):
    """今日学習した内容。"""

    content: str = Field(
        min_length=1,
        max_length=3000,
    )


class ChatResponse(BaseModel):
    """チャットAPIのレスポンス。"""

    message: str


# ============================================================
# Temporary State
# ============================================================


class ChatState(BaseModel):
    """現在のチャット状態。

    モック段階ではメモリ上に保持する。
    将来的にはDynamoDBに置き換える。
    """

    last_message: Optional[str] = None
    last_reply: Optional[str] = None

    explanation: Optional[str] = None
    feedback: Optional[str] = None

    today_content: Optional[str] = None
    question: Optional[str] = None


_state = ChatState()


# ============================================================
# Message
# ============================================================


@router.post(
    "/message",
    response_model=ChatResponse,
)
def send_message(request: MessageRequest) -> ChatResponse:
    """
    ユーザーのメッセージを受け取る。

    現在はモックの返答を生成する。
    """

    reply = generate_reply(request.message)

    _state.last_message = request.message
    _state.last_reply = reply

    return ChatResponse(
        message=request.message
    )


# ============================================================
# Reply
# ============================================================


@router.get(
    "/reply",
    response_model=ChatResponse,
)
def get_reply() -> ChatResponse:
    """
    AIからの返答を取得する。

    現在はモックの返答。
    """

    if _state.last_reply is None:
        return ChatResponse(
            message="まだメッセージが送信されていません。"
        )

    return ChatResponse(
        message=_state.last_reply
    )


# ============================================================
# Explanation
# ============================================================


@router.post(
    "/explanation",
    response_model=ChatResponse,
)
def send_explanation(
    request: ExplanationRequest,
) -> ChatResponse:
    """
    ユーザーが今日学習した内容を説明する。
    """

    feedback = generate_feedback(
        request.explanation
    )

    _state.explanation = request.explanation
    _state.feedback = feedback

    return ChatResponse(
        message=request.explanation
    )


# ============================================================
# Feedback
# ============================================================


@router.get(
    "/feedback",
    response_model=ChatResponse,
)
def get_feedback() -> ChatResponse:
    """
    AIからのフィードバックを取得する。
    """

    if _state.feedback is None:
        return ChatResponse(
            message="まだ説明が送信されていません。"
        )

    return ChatResponse(
        message=_state.feedback
    )


# ============================================================
# Today's Content
# ============================================================


@router.post(
    "/today",
    response_model=ChatResponse,
)
def send_today_content(
    request: TodayContentRequest,
) -> ChatResponse:
    """
    今日学習した内容を送信する。
    """

    question = generate_question(
        request.content
    )

    _state.today_content = request.content
    _state.question = question

    return ChatResponse(
        message=request.content
    )


# ============================================================
# Question
# ============================================================


@router.get(
    "/question",
    response_model=ChatResponse,
)
def get_question() -> ChatResponse:
    """
    AIからの出題を取得する。
    """

    if _state.question is None:
        return ChatResponse(
            message="まだ今日の学習内容が送信されていません。"
        )

    return ChatResponse(
        message=_state.question
    )