"""SQLAlchemy ORMモデル。

機能ごとにモデルを追加していく。テーブルは全て同一のDBインスタンスに置く。
"""

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, ForeignKey, Integer, Numeric, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    bases: Mapped[list["StudyBase"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class StudyBase(Base):
    """勉強拠点（図書館・学校・塾・自宅）。"""

    __tablename__ = "bases"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    category: Mapped[str] = mapped_column(String(20), nullable=False)
    latitude: Mapped[Decimal] = mapped_column(Numeric(9, 6), nullable=False)
    longitude: Mapped[Decimal] = mapped_column(Numeric(9, 6), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    user: Mapped["User"] = relationship(back_populates="bases")


class Character(Base):
    """キャラクターと育成状態を永続化するテーブル。

    総勉強時間と累計ペナルティ時間を計算の基準として保持する。
    levelなどの派生値はAPIの更新処理で再計算し、画面表示時の再計算を避ける。
    """

    __tablename__ = "characters"

    # キャラクターを一意に識別するUUID。INSERT時に自動生成される。
    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # 利用者が設定するキャラクター名。
    name: Mapped[str] = mapped_column(String(50), nullable=False)

    # これまでに登録された勉強時間の合計（分）。ペナルティがあっても減らさない。
    total_study_minutes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # 未学習日により差し引かれたペナルティ時間の累計（分）。
    total_penalty_minutes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # レベル計算に使う時間（分）。総勉強時間－累計ペナルティ時間、最低0。
    effective_study_minutes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # 有効勉強時間から算出した現在レベル（1～100）。
    level: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    # 過去に一度でも到達した最も高いレベル。ペナルティでは下がらない。
    highest_level: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    # ペナルティによる最低保証レベル。max(最高レベル－10, 1)。
    minimum_level: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    # 現在レベルに対応する進化段階（0～4）。
    evolution_stage: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # 現在レベルから次のレベルまでに必要な残り勉強時間（分）。
    remaining_minutes_to_next_level: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )
    # 最後に勉強時間を登録した日時。DBにはタイムゾーン付きで保存する。
    last_studied_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # この日まで未学習ペナルティを適用済みであることを表す日付。
    penalty_applied_through: Mapped[date | None] = mapped_column(Date, nullable=True)
