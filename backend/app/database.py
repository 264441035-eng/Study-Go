"""DB接続の共通基盤。

アプリ全体で1つのDBインスタンス（本番はRDS/PostgreSQL）を共有し、
機能ごとにテーブルを追加していく方針。接続先は環境変数 DATABASE_URL で切り替える。
"""

import os
import time

from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

# ローカル動作確認用のダミー値。本番は必ず環境変数 DATABASE_URL でRDSのエンドポイントを指定する。
# 空文字も未設定とみなす（import 時の create_engine("") を避け、init_db 側で明確にエラーにするため）。
DATABASE_URL = (
    os.getenv("DATABASE_URL")
    or "postgresql+psycopg2://study_go:study_go@localhost:5432/study_go"
)

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db() -> Session:
    """リクエストスコープのDBセッションを提供する依存関数。"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db(retries: int = 10, delay_seconds: float = 3.0) -> None:
    """テーブルを作成する（デプロイ時に明示実行するスキーマ初期化）。

    コンテナ起動(uvicorn)からは切り離し、`python -m app.dbctl init-db` として
    実行する。DATABASE_URL 未設定時はローカルの localhost に黙って接続せず、
    即座にエラーで停止する（本番の設定漏れを静かなクラッシュループにしないため）。
    DB 起動直後は接続不可のことがあるため数回リトライする。
    本番でスキーマ変更が頻発する場合はAlembic等への置き換えを推奨。
    """
    if not os.getenv("DATABASE_URL"):
        raise RuntimeError(
            "DATABASE_URL が未設定です。init_db は接続先の明示指定を要求します"
            "（localhost フォールバックには接続しません）。"
        )

    import app.models  # noqa: F401  モデル定義をmetadataに登録するため

    last_error: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            Base.metadata.create_all(bind=engine)
            return
        except OperationalError as exc:  # DB 起動直後などで接続不可のことがある
            last_error = exc
            if attempt < retries:
                print(
                    f"init_db: DB へ接続できません (試行 {attempt}/{retries})、"
                    f"{delay_seconds}s 後に再試行します",
                    flush=True,
                )
                time.sleep(delay_seconds)

    raise RuntimeError(
        f"init_db: {retries} 回試行しても DB に接続できませんでした"
    ) from last_error
