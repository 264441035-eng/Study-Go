"""DB接続の共通基盤。

アプリ全体で1つのDBインスタンス（本番はRDS/PostgreSQL）を共有し、
機能ごとにテーブルを追加していく方針。接続先は環境変数 DATABASE_URL で切り替える。
"""

import os

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

# ローカル動作確認用のダミー値。本番は必ず環境変数 DATABASE_URL でRDSのエンドポイントを指定する。
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg2://study_go:study_go@localhost:5432/study_go",
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


def init_db() -> None:
    """テーブルを作成する（開発用の簡易セットアップ）。

    本番運用ではAlembic等のマイグレーションツールに置き換えることを推奨。
    """
    import app.models  # noqa: F401  モデル定義をmetadataに登録するため

    Base.metadata.create_all(bind=engine)
