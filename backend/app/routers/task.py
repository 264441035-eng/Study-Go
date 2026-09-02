"""タスク(task)機能に関するエンドポイント。

新しい機能を追加するときは、この routers/ 配下に
このファイルのような <機能名>.py を作成し、
main.py で `app.include_router(...)` を1行追加するだけで良い。
"""

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from enum import Enum
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.routers.base import credit_study_time_by_location
from app.routers.character import (
    add_study_minutes_to_character,
    get_or_create_demo_character,
    utc_now,
)

JST = timezone(timedelta(hours=9))

router = APIRouter(prefix="/api/tasks", tags=["task"])


# =========================================================
# タスクの達成方法
# =========================================================


class CompletionMode(str, Enum):
    AUTO_TIME = "auto_time"
    MANUAL = "manual"
    EXTERNAL = "external"


# =========================================================
# 勉強タスク
# =========================================================


class StudyTask(BaseModel):
    id: int
    title: str
    minute: float | None = None
    done: bool = False

    # このレベル以上で表示
    required_level: int = 1

    # 空リストなら、どの拠点でも表示
    base_categories: list[str] = Field(default_factory=list)

    # 自動達成 / 手動達成 / 他機能から達成
    completion_mode: CompletionMode = CompletionMode.MANUAL


# =========================================================
# 運動タスク
# =========================================================


class ExerciseTask(BaseModel):
    id: int
    title: str
    done: bool = False

    required_level: int = 1

    base_categories: list[str] = Field(default_factory=list)

    completion_mode: CompletionMode = CompletionMode.MANUAL


# =========================================================
# 達成状況変更用
# =========================================================


class TaskStatusUpdate(BaseModel):
    done: bool


class TaskStatus(BaseModel):
    id: int
    title: str
    done: bool


# =========================================================
# 勉強時間関係
# =========================================================


class StudyTimeRequest(BaseModel):
    # 秒単位で受け取る
    seconds: int = Field(gt=0, le=86400)

    # 勉強終了時点の位置情報（任意）。ログイン中かつこれが送られてきた場合、
    # 最も近い自分の拠点（BASE_MATCH_RADIUS_METERS以内）に勉強時間を加算する。
    latitude: Decimal | None = None
    longitude: Decimal | None = None


class StudyRecord(BaseModel):
    seconds: int
    recorded_at: datetime


class StudyTimeSummary(BaseModel):
    today_seconds: int
    today_minutes: float
    studying: bool


class StudyStartResponse(BaseModel):
    started_at: str


class StudyTimeSendResponse(BaseModel):
    session_seconds: int
    today_seconds: int
    today_minutes: float
    auto_completed_task_ids: list[int]
    should_rest: bool

    # 位置情報から拠点を特定できた場合のみ入る。
    matched_base_id: UUID | None = None
    base_level: int | None = None
    base_leveled_up: bool = False


# =========================================================
# デモ用タスク
# =========================================================


_study_tasks: list[StudyTask] = [
    StudyTask(
        id=1,
        title="30秒勉強する（デモ）",
        minute=0.5,
        required_level=1,
        completion_mode=CompletionMode.AUTO_TIME,
    ),
    StudyTask(
        id=2,
        title="AIにやったことを説明する",
        minute=None,
        required_level=2,
        completion_mode=CompletionMode.EXTERNAL,
    ),
    StudyTask(
        id=3,
        title="AIの問題に答える",
        minute=None,
        required_level=3,
        completion_mode=CompletionMode.EXTERNAL,
    ),
]


_exercise_tasks: list[ExerciseTask] = [
    ExerciseTask(
        id=101,
        title="拠点まで徒歩で移動する",
        required_level=1,
        completion_mode=CompletionMode.EXTERNAL,
    ),
    ExerciseTask(
        id=102,
        title="散歩する",
        required_level=1,
        completion_mode=CompletionMode.MANUAL,
    ),
    ExerciseTask(
        id=103,
        title="スクワットする",
        required_level=2,
        completion_mode=CompletionMode.MANUAL,
    ),
]


# =========================================================
# 仮の保存場所
# =========================================================

# TODO:
# 現在はメモリ保存。
# DB導入後はDBへ置き換える。

_study_records: list[StudyRecord] = []

_study_started_at: datetime | None = None

_status_date: date = datetime.now(JST).date()


# =========================================================
# 内部処理
# =========================================================


def _now() -> datetime:
    return datetime.now(JST)


def _reset_daily_status_if_needed() -> None:
    """日付が変わったらタスク達成状態をリセットする。"""

    global _status_date
    global _study_started_at

    today = _now().date()

    if today == _status_date:
        return

    for task in _study_tasks:
        task.done = False

    for task in _exercise_tasks:
        task.done = False

    _study_started_at = None
    _status_date = today


def _today_study_seconds() -> int:
    """今日の勉強時間の合計を求める。"""

    today = _now().date()

    return sum(
        record.seconds
        for record in _study_records
        if record.recorded_at.date() == today
    )


def _apply_study_auto_completion() -> list[int]:
    """勉強時間による自動タスク達成を判定する。"""

    total_seconds = _today_study_seconds()

    completed_ids: list[int] = []

    for task in _study_tasks:
        if task.completion_mode != CompletionMode.AUTO_TIME:
            continue

        if task.minute is None:
            continue

        required_seconds = task.minute * 60

        if total_seconds >= required_seconds and not task.done:
            task.done = True
            completed_ids.append(task.id)

    return completed_ids


# =========================================================
# ホーム画面用API
# =========================================================


@router.get(
    "/context/study-time",
    response_model=StudyTimeSummary,
)
def get_today_study_time() -> StudyTimeSummary:
    """今日勉強した時間を返す。"""

    _reset_daily_status_if_needed()

    seconds = _today_study_seconds()

    return StudyTimeSummary(
        today_seconds=seconds,
        today_minutes=round(seconds / 60, 1),
        studying=_study_started_at is not None,
    )


@router.get(
    "/context/study-status",
    response_model=list[TaskStatus],
)
def get_study_task_status() -> list[TaskStatus]:
    """勉強タスクの達成状況を返す。"""

    _reset_daily_status_if_needed()

    return [
        TaskStatus(
            id=task.id,
            title=task.title,
            done=task.done,
        )
        for task in _study_tasks
    ]


@router.get(
    "/context/exercise-status",
    response_model=list[TaskStatus],
)
def get_exercise_task_status() -> list[TaskStatus]:
    """運動タスクの達成状況を返す。"""

    _reset_daily_status_if_needed()

    return [
        TaskStatus(
            id=task.id,
            title=task.title,
            done=task.done,
        )
        for task in _exercise_tasks
    ]


# =========================================================
# 勉強開始API
# =========================================================


@router.post(
    "/study/start",
    status_code=201,
    response_model=StudyStartResponse,
)
def start_study() -> StudyStartResponse:
    """勉強開始を宣言する。"""

    global _study_started_at

    _reset_daily_status_if_needed()

    if _study_started_at is not None:
        raise HTTPException(
            status_code=409,
            detail="Study session is already active",
        )

    _study_started_at = _now()

    return StudyStartResponse(
        started_at=_study_started_at.isoformat(),
    )


# =========================================================
# 勉強時間送信API
# =========================================================


@router.post(
    "/study/time",
    response_model=StudyTimeSendResponse,
)
def send_study_time(
    request: StudyTimeRequest,
    db: Session = Depends(get_db),
) -> StudyTimeSendResponse:
    """1回の勉強時間を保存する。

    位置情報が送られてきた場合は、最寄りの拠点に勉強時間を加算して
    拠点レベルも更新する。位置情報なしでも今まで通りタスクの自動達成判定は行う。
    """

    global _study_started_at

    _reset_daily_status_if_needed()

    if _study_started_at is None:
        raise HTTPException(
            status_code=400,
            detail="Study session has not been started",
        )

    _study_records.append(
        StudyRecord(
            seconds=request.seconds,
            recorded_at=_now(),
        )
    )

    _study_started_at = None

    completed_ids = _apply_study_auto_completion()

    total_seconds = _today_study_seconds()

    # 50分以上連続で勉強したら休憩を提案
    should_rest = request.seconds >= 50 * 60

    matched_base_id: UUID | None = None
    base_level: int | None = None
    base_leveled_up = False

    # Characterは分単位で管理するため、1分未満の秒数は切り捨てる。
    # ログインのないデモでは、DBの先頭の1体（なければ新規作成）へ加算する。
    study_minutes = request.seconds // 60
    if study_minutes > 0:
        character = get_or_create_demo_character(db, for_update=True)
        add_study_minutes_to_character(character, study_minutes, utc_now())

    if request.latitude is not None and request.longitude is not None:
        credited = credit_study_time_by_location(
            db, request.latitude, request.longitude, request.seconds
        )
        if credited is not None:
            base, base_leveled_up = credited
            matched_base_id = base.id
            base_level = base.level

    db.commit()

    return StudyTimeSendResponse(
        session_seconds=request.seconds,
        today_seconds=total_seconds,
        today_minutes=round(total_seconds / 60, 1),
        auto_completed_task_ids=completed_ids,
        should_rest=should_rest,
        matched_base_id=matched_base_id,
        base_level=base_level,
        base_leveled_up=base_leveled_up,
    )


# =========================================================
# タスク管理画面
# =========================================================


@router.get(
    "/study",
    response_model=list[StudyTask],
)
def list_study_tasks(
    level: int = 1,
    base_category: str | None = None,
) -> list[StudyTask]:
    """現在のレベル・拠点に応じた勉強タスクを返す。"""

    _reset_daily_status_if_needed()

    result: list[StudyTask] = []

    for task in _study_tasks:
        if task.required_level > level:
            continue

        if (
            base_category is not None
            and task.base_categories
            and base_category not in task.base_categories
        ):
            continue

        result.append(task)

    return result


@router.get(
    "/exercise",
    response_model=list[ExerciseTask],
)
def list_exercise_tasks(
    level: int = 1,
    base_category: str | None = None,
) -> list[ExerciseTask]:
    """現在のレベル・拠点に応じた運動タスクを返す。"""

    _reset_daily_status_if_needed()

    result: list[ExerciseTask] = []

    for task in _exercise_tasks:
        if task.required_level > level:
            continue

        if (
            base_category is not None
            and task.base_categories
            and base_category not in task.base_categories
        ):
            continue

        result.append(task)

    return result


# =========================================================
# 達成状況送信
# =========================================================


@router.post(
    "/study/{task_id}/status",
    response_model=StudyTask,
)
def update_study_task_status(
    task_id: int,
    update: TaskStatusUpdate,
) -> StudyTask:
    """勉強タスクの達成状況を変更する。"""

    _reset_daily_status_if_needed()

    for task in _study_tasks:
        if task.id == task_id:
            task.done = update.done
            return task

    raise HTTPException(
        status_code=404,
        detail="Study task not found",
    )


@router.post(
    "/exercise/{task_id}/status",
    response_model=ExerciseTask,
)
def update_exercise_task_status(
    task_id: int,
    update: TaskStatusUpdate,
) -> ExerciseTask:
    """運動タスクの達成状況を変更する。"""

    _reset_daily_status_if_needed()

    for task in _exercise_tasks:
        if task.id == task_id:
            task.done = update.done
            return task

    raise HTTPException(
        status_code=404,
        detail="Exercise task not found",
    )
