"""drop stale bases.user_id column

旧設計ではログイン機能があり、bases は User テーブルに紐づいていた
（StudyBase.user_id UUID NOT NULL, FK -> users.id）。その後アプリは
「ログイン無し・拠点はグローバルなデータ」方針に変わり、models.py から
user_id / User を削除した。しかし Alembic 導入前は create_all 運用で、
create_all は既存テーブルの列を DROP しないため、本番 RDS の bases には
user_id NOT NULL が取り残されている。

その結果、拠点登録 POST の INSERT が user_id を含めず NOT NULL 制約違反で
500 になる（GET は SELECT がモデル列のみ選ぶので成功していた）。
このリビジョンで残存列を削除して解消する。

冪等性: ローカル/新規 DB は現行モデルから作られ user_id を持たないため、
存在するときだけ DROP する（autogenerate では検出されないので手書き）。

Revision ID: 0002
Revises: 0001
Create Date: 2026-09-02

"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _bases_columns() -> set[str]:
    return {c["name"] for c in sa.inspect(op.get_bind()).get_columns("bases")}


def upgrade() -> None:
    # 本番 RDS にのみ残存する列。ローカル/新規 DB には無いのでスキップする。
    if "user_id" in _bases_columns():
        # FK 制約（bases.user_id -> users.id）は列と一緒に自動で落ちる。
        op.drop_column("bases", "user_id")


def downgrade() -> None:
    # 旧スキーマへ戻す（nullable=True で復元。既存行を壊さないため）。
    if "user_id" not in _bases_columns():
        op.add_column("bases", sa.Column("user_id", sa.Uuid(as_uuid=True), nullable=True))
