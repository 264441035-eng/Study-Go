"""Pydanticスキーマ。"""

from datetime import datetime
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
