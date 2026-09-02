"""JWT 認証 (HS256)。

既存 Backend が発行した JWT を検証し、claim の user_id を信頼する
(計画 §1-①: なりすまし防止。リクエストボディの user_id は使わない)。
共有シークレットは既存 Backend と同じ (settings.jwt_secret)。
"""

from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, Header, HTTPException, status

from app.config import Settings, get_settings


class AuthError(HTTPException):
    def __init__(self, detail: str) -> None:
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"},
        )


def create_access_token(
    user_id: str, settings: Settings, expires_in: timedelta = timedelta(hours=12)
) -> str:
    """開発/テスト用のトークン発行。

    本番のトークン発行元は既存 Backend の /login (計画 §1-①-B1)。
    ここでは backend 未実装でもローカルで疎通確認できるよう同じ形の
    トークンを作れるようにしておく。
    """
    now = datetime.now(timezone.utc)
    payload = {
        "user_id": user_id,
        "iat": now,
        "exp": now + expires_in,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def _extract_bearer(authorization: str | None) -> str:
    if not authorization:
        raise AuthError("Missing Authorization header")
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise AuthError("Invalid Authorization header (expected 'Bearer <token>')")
    return parts[1]


def verify_token(token: str, settings: Settings) -> str:
    """トークンを検証し user_id を返す。失敗時は 401。"""
    try:
        payload = jwt.decode(
            token, settings.jwt_secret, algorithms=[settings.jwt_algorithm]
        )
    except jwt.PyJWTError as e:
        raise AuthError(f"Invalid token: {e}") from e
    user_id = payload.get("user_id") or payload.get("sub")
    if not user_id:
        raise AuthError("Token missing user_id claim")
    return str(user_id)


def get_current_user_id(
    authorization: str | None = Header(default=None),
    settings: Settings = Depends(get_settings),
) -> str:
    """FastAPI 依存: 認証済みユーザーの user_id を返す。

    使い方: `def endpoint(user_id: str = Depends(get_current_user_id))`
    """
    token = _extract_bearer(authorization)
    return verify_token(token, settings)
