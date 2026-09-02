"""ログイン認証エンドポイント。

事前に ``AUTH_USERS`` へ登録した ID/パスワードで認証し、成功したら AI Tutor 用の
JWT を返す。新規登録は無い（軽量ログイン B案。詳細は app/auth.py）。
"""

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from app.auth import authenticate, create_access_token

router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginRequest(BaseModel):
    user_id: str
    password: str


class LoginResponse(BaseModel):
    token: str
    user_id: str


@router.post("/login", response_model=LoginResponse)
def login(body: LoginRequest) -> LoginResponse:
    if not authenticate(body.user_id, body.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="IDまたはパスワードが正しくありません。",
        )
    return LoginResponse(token=create_access_token(body.user_id), user_id=body.user_id)
