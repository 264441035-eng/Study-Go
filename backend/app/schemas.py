"""Pydanticスキーマ。"""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

BASE_CATEGORIES = ("library", "school", "cram_school", "home")

# 自宅・学校は現実的に1人1件しかないはずなので、1ユーザーにつき1件までに制限する。
# 図書館・塾は複数拠点があり得るため無制限。
SINGLE_INSTANCE_CATEGORIES = ("school", "home")

BASE_CATEGORY_LABELS = {
    "library": "図書館",
    "school": "学校",
    "cram_school": "塾",
    "home": "自宅",
}


class BaseCreate(BaseModel):
    name: str = Field(min_length=1, max_length=50)
    category: str
    latitude: Decimal
    longitude: Decimal


class BaseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    name: str
    category: str
    latitude: Decimal
    longitude: Decimal
    created_at: datetime


class BaseCountOut(BaseModel):
    count: int


class CharacterCreate(BaseModel):
    """キャラクター作成時の入力。育成状態はサーバー側で決定する。"""

    name: str = Field(
        min_length=1,
        max_length=50,
        description="作成するキャラクターの名前（1～50文字）",
        examples=["Hero"],
    )


class StudyRequest(BaseModel):
    """勉強時間登録の入力。時間の単位は分。"""

    minutes: int = Field(
        gt=0,
        description="今回追加する勉強時間（分）。1以上を指定する",
        examples=[30],
    )


class CharacterOut(BaseModel):
    """保存した育成状態と、画面表示用の時間。"""

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(description="キャラクターを一意に識別するUUID")
    name: str = Field(description="キャラクター名")
    total_study_minutes: int = Field(description="登録された総勉強時間（分）")
    total_penalty_minutes: int = Field(description="累計ペナルティ時間（分）")
    effective_study_minutes: int = Field(
        description="レベル計算に使う時間（総勉強時間－累計ペナルティ時間、分）"
    )
    level: int = Field(description="有効勉強時間から算出した現在レベル（1～100）")
    highest_level: int = Field(description="過去に到達した最高レベル")
    minimum_level: int = Field(description="ペナルティで下がり得る最低保証レベル")
    evolution_stage: int = Field(description="現在の進化段階（0～4）")
    remaining_minutes_to_next_level: int = Field(
        description="次のレベルまでに必要な残り勉強時間（分）"
    )
    last_studied_at: datetime | None = Field(
        description="最後に勉強時間を登録した日時。APIでは日本時間で返す"
    )
    penalty_applied_through: date | None = Field(
        description="未学習ペナルティを適用済みの最終日"
    )
    total_study_time: str = Field(description="総勉強時間の表示値（時間:分）")
    total_penalty_time: str = Field(description="累計ペナルティ時間の表示値（時間:分）")
    effective_study_time: str = Field(description="有効勉強時間の表示値（時間:分）")
    remaining_time_to_next_level: str = Field(
        description="次のレベルまでの残り時間の表示値（時間:分）"
    )
