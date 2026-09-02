"""学生への配布用アクセストークン一括発行 CLI。

本番 (APP_ENV != local) では /dev/token が無効なため、事前にこのスクリプトで
学生ごとの JWT を発行して配布する。学生ごとに user_id を分けることで、日次上限
(MAX_SESSIONS_PER_DAY) が学生単位で効き、利用の追跡もできる。

トークンは配布先の環境と同じ JWT_SECRET で署名する必要がある。発行時に
デプロイ環境の値を渡すこと:
    JWT_SECRET=<本番と同じ値> python -m scripts.issue_student_tokens ...

例:
    # student01..student05 を 30 日有効で発行し、共有 URL を出力
    JWT_SECRET=... python -m scripts.issue_student_tokens \
        --base-url https://tutor.example.com \
        --days 30 student01 student02 student03 student04 student05

    # 名簿ファイル (1 行 1 user_id) から発行
    JWT_SECRET=... python -m scripts.issue_student_tokens \
        --base-url https://tutor.example.com --from-file roster.txt
"""

import argparse
import sys
from datetime import timedelta

from app.auth import create_access_token
from app.config import get_settings


def _read_user_ids(args: argparse.Namespace) -> list[str]:
    ids = list(args.user_ids)
    if args.from_file:
        with open(args.from_file, encoding="utf-8") as f:
            ids += [line.strip() for line in f if line.strip()]
    # 重複を除きつつ順序を保つ。
    seen: set[str] = set()
    unique = [i for i in ids if not (i in seen or seen.add(i))]
    if not unique:
        print("no user_ids given (pass them as args or via --from-file)", file=sys.stderr)
        raise SystemExit(1)
    return unique


def main() -> None:
    parser = argparse.ArgumentParser(description="学生配布用トークンを一括発行する")
    parser.add_argument("user_ids", nargs="*", help="発行対象の user_id (複数可)")
    parser.add_argument("--from-file", help="1 行 1 user_id の名簿ファイル")
    parser.add_argument("--days", type=int, default=30, help="有効期限 (日, 既定 30)")
    parser.add_argument(
        "--base-url",
        help="チャットの公開 URL (例 https://tutor.example.com)。指定すると配布用 URL を出力",
    )
    args = parser.parse_args()

    settings = get_settings()
    if settings.jwt_secret == "dev-insecure-secret-change-me":
        print(
            "warning: JWT_SECRET が既定値のままです。配布先と同じ本番シークレットを "
            "環境変数 JWT_SECRET で渡してください。",
            file=sys.stderr,
        )

    expires_in = timedelta(days=args.days)
    for user_id in _read_user_ids(args):
        token = create_access_token(user_id, settings, expires_in=expires_in)
        if args.base_url:
            base = args.base_url.rstrip("/")
            print(f"{user_id}\t{base}/#/chat?token={token}")
        else:
            print(f"{user_id}\t{token}")


if __name__ == "__main__":
    main()
