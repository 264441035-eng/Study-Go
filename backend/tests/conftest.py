"""pytest 共通フィクスチャ。

テストは実 Postgres（CI では backend ジョブの Postgres service）に対して走る。
DB は複数テストで共有されるため、各テストの前に全テーブルをクリーンにして
テスト間の状態リークを防ぐ。これがないと、例えば一覧APIを「保存した件数と完全一致」で
検証するテストが、先行テストの残存行によって落ちる。
"""

import pytest

import app.models  # noqa: F401  全モデルを metadata に登録するため
from app.database import Base, engine


@pytest.fixture(autouse=True)
def reset_database() -> None:
    """各テスト前にスキーマを作り直し、まっさらな DB 状態から開始する。"""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
