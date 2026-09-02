"""Alembic 実行環境。

接続先は環境変数 DATABASE_URL から取得する（app.database と同じ方針。
未設定時は localhost に黙って繋がず即エラーにして、本番の設定漏れを検知する）。
target_metadata に app のモデルを渡すことで `alembic revision --autogenerate`
が models.py との差分から ALTER 文を生成できる。
"""

import os
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool

from alembic import context

# app のモデルを metadata に登録する（autogenerate の比較対象）。
import app.models  # noqa: F401
from app.database import Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def _database_url() -> str:
    url = os.getenv("DATABASE_URL")
    if not url:
        raise RuntimeError(
            "DATABASE_URL が未設定です。alembic は接続先の明示指定を要求します"
            "（localhost フォールバックには接続しません）。"
        )
    return url


def run_migrations_offline() -> None:
    """URL だけで SQL を出力するオフラインモード。"""
    context.configure(
        url=_database_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """実 DB に接続してマイグレーションを適用するオンラインモード。"""
    section = config.get_section(config.config_ini_section, {})
    section["sqlalchemy.url"] = _database_url()
    connectable = engine_from_config(
        section,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
