"""タスク(task)機能に関するエンドポイント。

新しい機能を追加するときは、この routers/ 配下に
このファイルのような <機能名>.py を作成し、
main.py で `app.include_router(...)` を1行追加するだけで良い。
"""

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/api/tasks", tags=["task"])


class Task(BaseModel):
    title: str
    done: bool = False


class TaskOut(Task):
    id: int


# TODO: 現状はメモリ上に保持するだけの仮実装。
# DBを導入したら SQLAlchemy 等のリポジトリ層に置き換える。
_tasks: list[TaskOut] = []
_next_id = 1


@router.get("")
def list_tasks() -> list[TaskOut]:
    return _tasks


@router.get("/{task_id}")
def get_task(task_id: int) -> TaskOut | None:
    return next((t for t in _tasks if t.id == task_id), None)


@router.post("", status_code=201)
def create_task(task: Task) -> TaskOut:
    global _next_id
    created = TaskOut(id=_next_id, **task.model_dump())
    _tasks.append(created)
    _next_id += 1
    return created


@router.patch("/{task_id}")
def update_task(task_id: int, task: Task) -> TaskOut | None:
    for i, existing in enumerate(_tasks):
        if existing.id == task_id:
            updated = TaskOut(id=task_id, **task.model_dump())
            _tasks[i] = updated
            return updated
    return None
