"""拠点(base)機能に関するエンドポイント。

ユーザーが実際に勉強する場所（図書館・学校・塾・自宅）を登録し、
勉強セッションと紐づけるための機能。カフェ等の一時的な場所は対象外。

地図描画はフロントエンドがGoogle Maps JavaScript SDKを直接利用して行う想定のため、
バックエンドは拠点の緯度経度（座標）を返すところまでを担当する。
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models import StudyBase, User
from app.schemas import (
    BASE_CATEGORIES,
    BASE_CATEGORY_LABELS,
    SINGLE_INSTANCE_CATEGORIES,
    BaseCountOut,
    BaseCreate,
    BaseOut,
)

router = APIRouter(prefix="/api/v1/bases", tags=["base"])


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


def _ensure_category_capacity(db: Session, user_id: UUID, category: str) -> None:
    if category not in SINGLE_INSTANCE_CATEGORIES:
        return

    already_exists = (
        db.query(StudyBase)
        .filter(StudyBase.user_id == user_id, StudyBase.category == category)
        .first()
        is not None
    )
    if already_exists:
        label = BASE_CATEGORY_LABELS[category]
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{label}は既に登録されています（1件まで）。削除してから登録し直してください",
        )


def _get_owned_base_or_404(db: Session, base_id: UUID, user_id: UUID) -> StudyBase:
    base = (
        db.query(StudyBase)
        .filter(StudyBase.id == base_id, StudyBase.user_id == user_id)
        .first()
    )
    if base is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="拠点が見つかりません")
    return base


@router.post("", response_model=BaseOut, status_code=status.HTTP_201_CREATED)
def create_base(
    payload: BaseCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> StudyBase:
    """拠点登録API。"""
    _validate_base_input(payload)
    _ensure_category_capacity(db, current_user.id, payload.category)

    base = StudyBase(
        user_id=current_user.id,
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
def list_bases(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[StudyBase]:
    """拠点座標API。自分が登録した全拠点（緯度経度を含む）を返す。"""
    return (
        db.query(StudyBase)
        .filter(StudyBase.user_id == current_user.id)
        .order_by(StudyBase.created_at)
        .all()
    )


@router.get("/count", response_model=BaseCountOut)
def count_bases(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> BaseCountOut:
    """拠点の数API。自分が登録した拠点の件数を返す。"""
    count = (
        db.query(func.count(StudyBase.id))
        .filter(StudyBase.user_id == current_user.id)
        .scalar()
    )
    return BaseCountOut(count=count or 0)


@router.get("/{base_id}", response_model=BaseOut)
def get_base(
    base_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> StudyBase:
    return _get_owned_base_or_404(db, base_id, current_user.id)


@router.delete("/{base_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_base(
    base_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    base = _get_owned_base_or_404(db, base_id, current_user.id)
    db.delete(base)
    db.commit()
