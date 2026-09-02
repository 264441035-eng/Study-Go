"""DB 運用コマンド（スキーマ初期化など）。

コンテナ起動(uvicorn)から切り離し、デプロイ時に one-off タスクとして
`python -m app.dbctl init-db` の形で明示的に実行する。CI のスモークテストでも
同じコマンドで本番と同じ初期化経路を検証する。
"""

import sys

from app.database import init_db


def main(argv: list[str]) -> int:
    cmd = argv[1] if len(argv) > 1 else ""
    if cmd == "init-db":
        init_db()
        print("init-db: 完了")
        return 0
    print("usage: python -m app.dbctl init-db", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
