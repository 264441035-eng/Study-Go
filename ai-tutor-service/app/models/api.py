"""Public API のリクエスト/レスポンススキーマ。

内部 Tool Calling の中身は返さない (計画 §4 / 仕様書12章)。
"""

from pydantic import BaseModel, Field


class StartSessionResponse(BaseModel):
    session_id: str
    message: str


class SendMessageRequest(BaseModel):
    message: str = Field(min_length=1)


class SendMessageResponse(BaseModel):
    message: str
    state: str  # "questioning" | "ready_to_finish"


class FinishResponse(BaseModel):
    session_id: str
    score: int
    summary: str
    strengths: list[str]
    weaknesses: list[str]
    xp: int
