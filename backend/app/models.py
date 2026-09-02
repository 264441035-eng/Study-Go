"""SQLAlchemy ORMモデル。

機能ごとにモデルを追加していく。テーブルは全て同一のDBインスタンスに置く。
"""

import uuid
from bisect import bisect_right
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from functools import lru_cache

from sqlalchemy import DateTime, Integer, Numeric, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


# =========================================================
# レベル計算（拠点のレベルアップに使う成長曲線）
# =========================================================


@dataclass(frozen=True)
class LevelCurve:
    """「レベルが上がるほど必要時間が増える」成長曲線の設定。

    ``growth_interval_levels`` レベルごとに、必要時間が
    ``growth_units_per_level`` ずつ増えていく。
    """

    base_units_per_level: int
    growth_units_per_level: int
    growth_interval_levels: int
    max_level: int


def _required_units_for_next_level(level: int, curve: LevelCurve) -> int:
    tier = (level - 1) // curve.growth_interval_levels
    return curve.base_units_per_level + curve.growth_units_per_level * tier


@lru_cache(maxsize=None)
def _thresholds(curve: LevelCurve) -> tuple[int, ...]:
    """各レベルに到達するために必要な累積時間の一覧。

    index 0 がレベル1（0時間で到達）、index 1 がレベル2への到達時間、…
    """
    thresholds = [0]
    total = 0
    for level in range(1, curve.max_level):
        total += _required_units_for_next_level(level, curve)
        thresholds.append(total)
    return tuple(thresholds)


def calculate_level(total_units: int, curve: LevelCurve) -> tuple[int, int]:
    """累積時間から (現在レベル, 次のレベルまでの残り時間) を返す。

    最大レベルに達している場合、残り時間は0。
    """
    thresholds = _thresholds(curve)
    level = min(bisect_right(thresholds, total_units), curve.max_level)
    if level == curve.max_level:
        return curve.max_level, 0
    return level, thresholds[level] - total_units


# 拠点レベルの成長曲線（秒単位）。10レベルごとに必要時間が1時間ずつ伸びていく
# （暫定値。ゲームバランスは今後調整）。
BASE_LEVEL_CURVE = LevelCurve(
    base_units_per_level=3600,
    growth_units_per_level=3600,
    growth_interval_levels=10,
    max_level=100,
)


# =========================================================
# テーブル定義
# =========================================================


class StudyBase(Base):
    """勉強拠点（図書館・学校・塾・自宅）。

    このアプリは他機能（task, character）と同様にログイン機能を持たないため、
    拠点もユーザーに紐付かないグローバルなデータとして扱う。
    """

    __tablename__ = "bases"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    category: Mapped[str] = mapped_column(String(20), nullable=False)
    latitude: Mapped[Decimal] = mapped_column(Numeric(9, 6), nullable=False)
    longitude: Mapped[Decimal] = mapped_column(Numeric(9, 6), nullable=False)
    # その拠点で勉強した累積時間（秒）。拠点レベルはこの値から算出する。
    total_study_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    level: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    def add_study_seconds(self, seconds: int) -> bool:
        """勉強時間を加算し、拠点レベルを再計算する。レベルが上がったらTrueを返す。"""
        previous_level = self.level
        self.total_study_seconds += seconds
        self.level, _ = calculate_level(self.total_study_seconds, BASE_LEVEL_CURVE)
        return self.level > previous_level
