"""create tasks table and seed default tasks

勉強/運動タブに表示する既製タスクのテーブル tasks を追加し、
初期タスク（app.task_seed.DEFAULT_TASKS）を投入する。
models.py の Task に対応する。

冪等性: 0001 と同じ方針で、テーブルが存在しないときだけ作成する。
初期データも「まだ1件も無いときだけ」投入し、再実行や既存DBで重複しないようにする。

Revision ID: 0003
Revises: 0002
Create Date: 2026-09-03

"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op
from app.task_seed import DEFAULT_TASKS

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _existing_tables() -> set[str]:
    return set(sa.inspect(op.get_bind()).get_table_names())


def upgrade() -> None:
    if "tasks" not in _existing_tables():
        tasks = op.create_table(
            "tasks",
            sa.Column("id", sa.Integer(), autoincrement=False, nullable=False),
            sa.Column("category", sa.String(length=20), nullable=False),
            sa.Column("title", sa.String(length=100), nullable=False),
            sa.Column("minute", sa.Float(), nullable=True),
            sa.Column(
                "required_level", sa.Integer(), server_default="1", nullable=False
            ),
            sa.Column(
                "base_categories", sa.String(length=100), server_default="", nullable=False
            ),
            sa.Column(
                "completion_mode",
                sa.String(length=20),
                server_default="manual",
                nullable=False,
            ),
            sa.Column("done", sa.Boolean(), server_default="false", nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )
    else:
        tasks = sa.table(
            "tasks",
            sa.column("id", sa.Integer),
            sa.column("category", sa.String),
            sa.column("title", sa.String),
            sa.column("minute", sa.Float),
            sa.column("required_level", sa.Integer),
            sa.column("base_categories", sa.String),
            sa.column("completion_mode", sa.String),
            sa.column("done", sa.Boolean),
        )

    # 初期タスクはまだ1件も無いときだけ投入する（再実行/既存DBで重複させない）。
    already = op.get_bind().execute(sa.text("SELECT COUNT(*) FROM tasks")).scalar()
    if not already:
        op.bulk_insert(
            tasks,
            [{**row, "done": False} for row in DEFAULT_TASKS],
        )


def downgrade() -> None:
    if "tasks" in _existing_tables():
        op.drop_table("tasks")
