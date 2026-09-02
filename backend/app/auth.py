"""ログイン認証と JWT 発行（AI Tutor 用）。

方針（軽量ログイン B案）:
  - 事前に決めた ID/パスワードを環境変数 ``AUTH_USERS`` に JSON で持つ。
    値は bcrypt ハッシュ（平文は置かない）。例:
      AUTH_USERS='{"student01": "$2b$12$...", "student02": "$2b$12$..."}'
    ハッシュは ``python -m scripts.hash_password`` で生成する。
  - ログイン成功時に JWT(HS256) を発行する。署名鍵・アルゴリズム・claim 形は
    ai-tutor-service/app/auth.py と揃える（同じ ``JWT_SECRET`` を共有し、
    ai-tutor 側でそのまま検証できるようにする）。

新規登録(register)は持たない。ユーザーは ``AUTH_USERS`` に列挙した分だけ。
"""

import json
import os
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

# ai-tutor と同じ既定値。ローカルでは ai-tutor の既定 JWT_SECRET と一致するため、
# backend が発行したトークンをローカルの ai-tutor がそのまま検証できる。
_DEFAULT_SECRET = "dev-insecure-secret-change-me"
_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
_TOKEN_TTL = timedelta(hours=12)


def _jwt_secret() -> str:
    return os.getenv("JWT_SECRET", _DEFAULT_SECRET)


def _load_users() -> dict[str, str]:
    """``AUTH_USERS`` (JSON: user_id -> bcrypt ハッシュ) を読む。未設定なら空。"""
    raw = os.getenv("AUTH_USERS")
    if not raw:
        return {}
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    if not isinstance(data, dict):
        return {}
    return {str(k): str(v) for k, v in data.items()}


def verify_password(password: str, hashed: str) -> bool:
    """平文パスワードが bcrypt ハッシュに一致するか。"""
    try:
        return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
    except ValueError:
        # ハッシュの形式が不正な場合など。
        return False


def authenticate(user_id: str, password: str) -> bool:
    """ユーザーが存在し、かつパスワードが一致すれば True。"""
    users = _load_users()
    hashed = users.get(user_id)
    if hashed is None:
        return False
    return verify_password(password, hashed)


def create_access_token(user_id: str, expires_in: timedelta = _TOKEN_TTL) -> str:
    """ai-tutor が検証できる形の JWT を発行する。"""
    now = datetime.now(timezone.utc)
    payload = {
        "user_id": user_id,
        "iat": now,
        "exp": now + expires_in,
    }
    return jwt.encode(payload, _jwt_secret(), algorithm=_ALGORITHM)
