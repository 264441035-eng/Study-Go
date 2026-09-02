"""todo（学習用の項目管理）機能に関するエンドポイント。

名称・カテゴリ（勉強/運動）・達成済みかどうかの3項目を持つ、
DB動作確認用のシンプルなCRUD機能。ログイン機能を持たないため、
task/character/base と同様にユーザーに紐付かないグローバルなデータとして扱う。
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import TodoItem
from app.schemas import TODO_CATEGORIES, TodoCreate, TodoOut, TodoStatusUpdate

router = APIRouter(prefix="/api/v1/todos", tags=["todo"])


def _validate_category(category: str) -> None:
    if category not in TODO_CATEGORIES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"category は {', '.join(TODO_CATEGORIES)} のいずれかを指定してください",
        )


def _get_todo_or_404(db: Session, todo_id: UUID) -> TodoItem:
    todo = db.query(TodoItem).filter(TodoItem.id == todo_id).first()
    if todo is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="項目が見つかりません")
    return todo


@router.post("", response_model=TodoOut, status_code=status.HTTP_201_CREATED)
def create_todo(payload: TodoCreate, db: Session = Depends(get_db)) -> TodoItem:
    """項目を登録する。"""
    _validate_category(payload.category)

    todo = TodoItem(
        name=payload.name,
        category=payload.category,
        done=payload.done,
    )
    db.add(todo)
    db.commit()
    db.refresh(todo)
    return todo


@router.get("", response_model=list[TodoOut])
def list_todos(db: Session = Depends(get_db)) -> list[TodoItem]:
    """登録済みの全項目を返す。"""
    return db.query(TodoItem).order_by(TodoItem.created_at).all()


@router.get("/{todo_id}", response_model=TodoOut)
def get_todo(todo_id: UUID, db: Session = Depends(get_db)) -> TodoItem:
    return _get_todo_or_404(db, todo_id)


@router.patch("/{todo_id}/status", response_model=TodoOut)
def update_todo_status(
    todo_id: UUID,
    payload: TodoStatusUpdate,
    db: Session = Depends(get_db),
) -> TodoItem:
    """達成状況（done）を更新する。"""
    todo = _get_todo_or_404(db, todo_id)
    todo.done = payload.done
    db.commit()
    db.refresh(todo)
    return todo


@router.delete("/{todo_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_todo(todo_id: UUID, db: Session = Depends(get_db)) -> None:
    todo = _get_todo_or_404(db, todo_id)
    db.delete(todo)
    db.commit()
