"""create todo_items table

タスク管理（学習用の項目管理）機能で使う todo_items テーブルを追加する。
models.py の TodoItem に対応する（名称・カテゴリ・達成済みフラグの3項目）。

冪等性: 0001 と同じ方針で、テーブルが存在しないときだけ作成する。
これにより新規 DB でも、（万一 create_all で先に作られている）既存 DB でも
安全に `alembic upgrade head` を流せる。

Revision ID: 0003
Revises: 0002
Create Date: 2026-09-03

"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _existing_tables() -> set[str]:
    return set(sa.inspect(op.get_bind()).get_table_names())


def upgrade() -> None:
    if "todo_items" not in _existing_tables():
        op.create_table(
            "todo_items",
            sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
            sa.Column("name", sa.String(length=50), nullable=False),
            sa.Column("category", sa.String(length=20), nullable=False),
            sa.Column(
                "done",
                sa.Boolean(),
                server_default="false",
                nullable=False,
            ),
            sa.Column(
                "created_at",
                sa.DateTime(),
                server_default=sa.text("now()"),
                nullable=False,
            ),
            sa.PrimaryKeyConstraint("id"),
        )


def downgrade() -> None:
    if "todo_items" in _existing_tables():
        op.drop_table("todo_items")
