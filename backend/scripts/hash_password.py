"""AUTH_USERS 用の bcrypt ハッシュ生成 CLI。

事前に決めた ID/パスワードから、環境変数 ``AUTH_USERS`` に入れる JSON を作る。
パスワードは標準入力で受け取り、コマンド履歴やログに平文を残さない。

例:
    # 1 ユーザー分のハッシュを出力
    python -m scripts.hash_password student01
        password: ****
        "student01": "$2b$12$..."

    # 複数ユーザーをまとめて AUTH_USERS の JSON にする
    python -m scripts.hash_password --json student01 student02
        {"student01": "$2b$12$...", "student02": "$2b$12$..."}
"""

import argparse
import getpass
import json

import bcrypt


def _hash(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="AUTH_USERS 用の bcrypt ハッシュを作る")
    parser.add_argument("user_ids", nargs="+", help="ハッシュを作る user_id (複数可)")
    parser.add_argument(
        "--json",
        action="store_true",
        help="AUTH_USERS にそのまま入れられる JSON で出力する",
    )
    args = parser.parse_args()

    result: dict[str, str] = {}
    for user_id in args.user_ids:
        password = getpass.getpass(f"password for {user_id}: ")
        result[user_id] = _hash(password)

    if args.json:
        print(json.dumps(result, ensure_ascii=False))
    else:
        for user_id, hashed in result.items():
            print(f'"{user_id}": "{hashed}"')


if __name__ == "__main__":
    main()
