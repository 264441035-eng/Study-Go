"""Public API のリクエスト/レスポンススキーマ。

内部 Tool Calling の中身は返さない (計画 §4 / 仕様書12章)。
"""

from pydantic import BaseModel, Field


class StartSessionRequest(BaseModel):
    # 進化前=tsundere / 進化後=onee。フロントが渡す口調(app.services.persona)。
    # 未指定でも動くよう任意にする（既定の親しみやすい口調になる）。
    persona: str | None = None


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
