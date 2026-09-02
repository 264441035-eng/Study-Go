"""initial schema (bases, characters)

現行スキーマ（models.py の StudyBase / Character）をそのまま表す初期リビジョン。

重要: 本番 RDS には既に bases / characters が存在する（Alembic 導入前は
create_all + 手動 ALTER で運用していた）。そのまま upgrade すると
「テーブルが既に存在する」で失敗するため、この初期リビジョンは
**存在しないテーブルだけ作成する冪等実装**にしてある。これにより
`alembic upgrade head` を、既存 prod でも空の新規 DB でも安全に流せる
（既存 DB では何も作らず、このリビジョンが適用済みとして記録されるだけ）。

以降のスキーマ変更は `alembic revision --autogenerate -m "..."` で
新リビジョンを追加すること（この冪等分岐は初期リビジョン限定）。

Revision ID: 0001
Revises:
Create Date: 2026-09-02

"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _existing_tables() -> set[str]:
    return set(sa.inspect(op.get_bind()).get_table_names())


def upgrade() -> None:
    existing = _existing_tables()

    if "bases" not in existing:
        op.create_table(
            "bases",
            sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
            sa.Column("name", sa.String(length=50), nullable=False),
            sa.Column("category", sa.String(length=20), nullable=False),
            sa.Column("latitude", sa.Numeric(precision=9, scale=6), nullable=False),
            sa.Column("longitude", sa.Numeric(precision=9, scale=6), nullable=False),
            sa.Column(
                "total_study_seconds",
                sa.Integer(),
                server_default="0",
                nullable=False,
            ),
            sa.Column("level", sa.Integer(), server_default="1", nullable=False),
            sa.Column(
                "created_at",
                sa.DateTime(),
                server_default=sa.text("now()"),
                nullable=False,
            ),
            sa.PrimaryKeyConstraint("id"),
        )

    if "characters" not in existing:
        op.create_table(
            "characters",
            sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
            sa.Column("name", sa.String(length=50), nullable=False),
            sa.Column("total_study_minutes", sa.Integer(), nullable=False),
            sa.Column("total_penalty_minutes", sa.Integer(), nullable=False),
            sa.Column("effective_study_minutes", sa.Integer(), nullable=False),
            sa.Column("level", sa.Integer(), nullable=False),
            sa.Column("highest_level", sa.Integer(), nullable=False),
            sa.Column("minimum_level", sa.Integer(), nullable=False),
            sa.Column("evolution_stage", sa.Integer(), nullable=False),
            sa.Column("remaining_minutes_to_next_level", sa.Integer(), nullable=False),
            sa.Column("last_studied_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("penalty_applied_through", sa.Date(), nullable=True),
            sa.PrimaryKeyConstraint("id"),
        )


def downgrade() -> None:
    op.drop_table("characters")
    op.drop_table("bases")
