"""拠点(base)機能に関するエンドポイント。

実際に勉強する場所（図書館・学校・塾・自宅）を登録し、勉強セッションと
紐づけるための機能。カフェ等の一時的な場所は対象外。

このアプリはログイン機能を持たないため（task/character機能と同様）、
拠点もユーザーに紐付かないグローバルなデータとして扱う。

地図描画はフロントエンドがGoogle Maps JavaScript SDKを直接利用して行う想定のため、
バックエンドは拠点の緯度経度（座標）を返すところまでを担当する。
"""

from decimal import Decimal
from math import atan2, cos, radians, sin, sqrt
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import StudyBase
from app.schemas import (
    BASE_CATEGORIES,
    BASE_CATEGORY_LABELS,
    SINGLE_INSTANCE_CATEGORIES,
    BaseCountOut,
    BaseCreate,
    BaseOut,
    StudyTimeAdd,
    StudyTimeAddOut,
)

router = APIRouter(prefix="/api/v1/bases", tags=["base"])

EARTH_RADIUS_METERS = 6_371_000
# この距離(m)以内に登録拠点があれば「そこで勉強した」とみなして加算する（暫定値）。
BASE_MATCH_RADIUS_METERS = 200


def _validate_base_input(payload: BaseCreate) -> None:
    if payload.category not in BASE_CATEGORIES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"category は {', '.join(BASE_CATEGORIES)} のいずれかを指定してください",
        )
    if not (-90 <= payload.latitude <= 90):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="latitude は -90 から 90 の範囲で指定してください",
        )
    if not (-180 <= payload.longitude <= 180):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="longitude は -180 から 180 の範囲で指定してください",
        )


def _ensure_category_capacity(db: Session, category: str) -> None:
    if category not in SINGLE_INSTANCE_CATEGORIES:
        return

    already_exists = db.query(StudyBase).filter(StudyBase.category == category).first() is not None
    if already_exists:
        label = BASE_CATEGORY_LABELS[category]
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{label}は既に登録されています（1件まで）。削除してから登録し直してください",
        )


def _get_base_or_404(db: Session, base_id: UUID) -> StudyBase:
    base = db.query(StudyBase).filter(StudyBase.id == base_id).first()
    if base is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="拠点が見つかりません")
    return base


def _distance_meters(lat1: Decimal, lon1: Decimal, lat2: Decimal, lon2: Decimal) -> float:
    """2地点間の距離をメートルで返す（球面上の大円距離、Haversine公式）。"""
    phi1, phi2 = radians(float(lat1)), radians(float(lat2))
    delta_phi = radians(float(lat2) - float(lat1))
    delta_lambda = radians(float(lon2) - float(lon1))

    a = sin(delta_phi / 2) ** 2 + cos(phi1) * cos(phi2) * sin(delta_lambda / 2) ** 2
    return 2 * EARTH_RADIUS_METERS * atan2(sqrt(a), sqrt(1 - a))


def _find_nearby_base(db: Session, latitude: Decimal, longitude: Decimal) -> StudyBase | None:
    """登録済みの拠点の中から、指定座標に最も近く、かつ許容範囲内のものを返す。"""
    bases = db.query(StudyBase).all()

    nearest: StudyBase | None = None
    nearest_distance = float("inf")

    for base in bases:
        distance = _distance_meters(latitude, longitude, base.latitude, base.longitude)
        if distance < nearest_distance:
            nearest = base
            nearest_distance = distance

    if nearest is not None and nearest_distance <= BASE_MATCH_RADIUS_METERS:
        return nearest
    return None


def credit_study_time_by_location(
    db: Session, latitude: Decimal, longitude: Decimal, seconds: int
) -> tuple[StudyBase, bool] | None:
    """指定座標に最も近い拠点（許容範囲内）に勉強時間を加算する。

    他機能（task.pyの勉強時間送信など）から、位置情報を渡すだけで
    拠点連携できるようにするための公開関数。マッチする拠点が無ければNone。
    """
    base = _find_nearby_base(db, latitude, longitude)
    if base is None:
        return None

    leveled_up = base.add_study_seconds(seconds)
    db.commit()
    db.refresh(base)
    return base, leveled_up


@router.post("", response_model=BaseOut, status_code=status.HTTP_201_CREATED)
def create_base(payload: BaseCreate, db: Session = Depends(get_db)) -> StudyBase:
    """拠点登録API。"""
    _validate_base_input(payload)
    _ensure_category_capacity(db, payload.category)

    base = StudyBase(
        name=payload.name,
        category=payload.category,
        latitude=payload.latitude,
        longitude=payload.longitude,
    )
    db.add(base)
    db.commit()
    db.refresh(base)
    return base


@router.get("", response_model=list[BaseOut])
def list_bases(db: Session = Depends(get_db)) -> list[StudyBase]:
    """拠点座標API。登録済みの全拠点（緯度経度を含む）を返す。"""
    return db.query(StudyBase).order_by(StudyBase.created_at).all()


@router.get("/count", response_model=BaseCountOut)
def count_bases(db: Session = Depends(get_db)) -> BaseCountOut:
    """拠点の数API。"""
    count = db.query(func.count(StudyBase.id)).scalar()
    return BaseCountOut(count=count or 0)


@router.get("/{base_id}", response_model=BaseOut)
def get_base(base_id: UUID, db: Session = Depends(get_db)) -> StudyBase:
    return _get_base_or_404(db, base_id)


@router.post("/{base_id}/study-time", response_model=StudyTimeAddOut)
def add_study_time(
    base_id: UUID,
    payload: StudyTimeAdd,
    db: Session = Depends(get_db),
) -> StudyTimeAddOut:
    """拠点での勉強時間を加算し、拠点レベルを再計算する。"""
    base = _get_base_or_404(db, base_id)
    leveled_up = base.add_study_seconds(payload.seconds)

    db.commit()
    db.refresh(base)

    return StudyTimeAddOut(
        **BaseOut.model_validate(base).model_dump(),
        leveled_up=leveled_up,
    )


@router.delete("/{base_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_base(base_id: UUID, db: Session = Depends(get_db)) -> None:
    base = _get_base_or_404(db, base_id)
    db.delete(base)
    db.commit()
