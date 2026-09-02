"""開発専用エンドポイント (APP_ENV=local のみ)。

本番の JWT 発行元は既存 Backend の POST /login (計画 §1-①-B1)。
backend 未実装でもフロントから会話を試せるよう、local に限り
デモ用トークンを払い出す。local 以外では 404。
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.auth import create_access_token
from app.config import Settings, get_settings

router = APIRouter(prefix="/dev", tags=["dev"])


class DevTokenRequest(BaseModel):
    user_id: str = "demo-student"


class DevTokenResponse(BaseModel):
    token: str
    user_id: str


@router.post("/token", response_model=DevTokenResponse)
def issue_dev_token(
    body: DevTokenRequest,
    settings: Settings = Depends(get_settings),
) -> DevTokenResponse:
    if settings.app_env != "local":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not available")
    return DevTokenResponse(
        token=create_access_token(body.user_id, settings), user_id=body.user_id
    )
