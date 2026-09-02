"""Pydanticスキーマ。"""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

BASE_CATEGORIES = ("library", "school", "cram_school", "home")


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
