"""タスク(task)機能に関するエンドポイント。

タスクの定義と完了状態は DB の tasks テーブルに保持する（既製タスクは
Alembic のデータマイグレーションで投入。app.task_seed.DEFAULT_TASKS 参照）。
ログイン機能が無いため、完了状態は全ユーザー共通のグローバルな値として扱う。
リセットは「デモ用リセットAPI」を叩いたときだけ行い、毎日の自動リセットはしない。

勉強セッション（開始時刻・今日の勉強秒数）は従来どおりメモリ保持のまま。
"""

import os
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from enum import Enum
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Task
from app.routers.base import credit_study_time_by_location
from app.routers.character import (
    add_study_minutes_to_character,
    get_or_create_demo_character,
    utc_now,
)

JST = timezone(timedelta(hours=9))

# タスクを1つ完了したときにキャラへ加算する経験値（分換算）。
# 経験値は勉強分数に一本化しているため、ボーナス勉強時間として加算する。
# デモは短時間で進化を見せたいので小さめ。本番では環境変数で調整する。
TASK_COMPLETION_XP_MINUTES = int(os.getenv("TASK_COMPLETION_XP_MINUTES", "3"))

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
# 仮の保存場所（勉強セッション）
# =========================================================

# 勉強セッション（開始時刻・今日の勉強記録）は従来どおりメモリ保持。
# タスクの完了状態は DB(tasks.done) に移したため、ここでは扱わない。

_study_records: list[StudyRecord] = []

_study_started_at: datetime | None = None

_status_date: date = datetime.now(JST).date()


# =========================================================
# 内部処理
# =========================================================


def _now() -> datetime:
    return datetime.now(JST)


def _reset_daily_study_session_if_needed() -> None:
    """日付が変わったら勉強セッションの開始状態をリセットする。

    タスクの完了状態(tasks.done)はデモ用リセットでのみ戻すため、ここでは触れない。
    """

    global _status_date
    global _study_started_at

    today = _now().date()

    if today == _status_date:
        return

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


def _parse_base_categories(raw: str) -> list[str]:
    """カンマ区切りの base_categories 文字列をリストへ変換する。"""

    return [c for c in (part.strip() for part in raw.split(",")) if c]


def _to_study_task(task: Task) -> StudyTask:
    return StudyTask(
        id=task.id,
        title=task.title,
        minute=task.minute,
        done=task.done,
        required_level=task.required_level,
        base_categories=_parse_base_categories(task.base_categories),
        completion_mode=CompletionMode(task.completion_mode),
    )


def _to_exercise_task(task: Task) -> ExerciseTask:
    return ExerciseTask(
        id=task.id,
        title=task.title,
        done=task.done,
        required_level=task.required_level,
        base_categories=_parse_base_categories(task.base_categories),
        completion_mode=CompletionMode(task.completion_mode),
    )


def _tasks_by_category(db: Session, category: str) -> list[Task]:
    """カテゴリのタスクを id 昇順で取得する。"""

    return list(
        db.scalars(
            select(Task).where(Task.category == category).order_by(Task.id)
        ).all()
    )


def _apply_study_auto_completion(db: Session) -> list[int]:
    """勉強時間による自動タスク達成を判定する（DBへ反映。commitは呼び出し元）。"""

    total_seconds = _today_study_seconds()

    completed_ids: list[int] = []

    for task in _tasks_by_category(db, "study"):
        if task.completion_mode != CompletionMode.AUTO_TIME.value:
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

    _reset_daily_study_session_if_needed()

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
def get_study_task_status(db: Session = Depends(get_db)) -> list[TaskStatus]:
    """勉強タスクの達成状況を返す。"""

    return [
        TaskStatus(id=task.id, title=task.title, done=task.done)
        for task in _tasks_by_category(db, "study")
    ]


@router.get(
    "/context/exercise-status",
    response_model=list[TaskStatus],
)
def get_exercise_task_status(db: Session = Depends(get_db)) -> list[TaskStatus]:
    """運動タスクの達成状況を返す。"""

    return [
        TaskStatus(id=task.id, title=task.title, done=task.done)
        for task in _tasks_by_category(db, "exercise")
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

    _reset_daily_study_session_if_needed()

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

    _reset_daily_study_session_if_needed()

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

    completed_ids = _apply_study_auto_completion(db)

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


def _list_tasks(
    db: Session,
    category: str,
    level: int,
    base_category: str | None,
) -> list[Task]:
    """レベル・拠点に応じて表示するタスクを絞り込む。"""

    result: list[Task] = []

    for task in _tasks_by_category(db, category):
        if task.required_level > level:
            continue

        allowed = _parse_base_categories(task.base_categories)
        if base_category is not None and allowed and base_category not in allowed:
            continue

        result.append(task)

    return result


@router.get(
    "/study",
    response_model=list[StudyTask],
)
def list_study_tasks(
    level: int = 1,
    base_category: str | None = None,
    db: Session = Depends(get_db),
) -> list[StudyTask]:
    """現在のレベル・拠点に応じた勉強タスクを返す。"""

    return [
        _to_study_task(task)
        for task in _list_tasks(db, "study", level, base_category)
    ]


@router.get(
    "/exercise",
    response_model=list[ExerciseTask],
)
def list_exercise_tasks(
    level: int = 1,
    base_category: str | None = None,
    db: Session = Depends(get_db),
) -> list[ExerciseTask]:
    """現在のレベル・拠点に応じた運動タスクを返す。"""

    return [
        _to_exercise_task(task)
        for task in _list_tasks(db, "exercise", level, base_category)
    ]


# =========================================================
# 達成状況送信
# =========================================================


def _award_task_completion_xp(db: Session) -> None:
    """タスク完了時にキャラへ経験値（ボーナス勉強時間）を加算する。

    ログインのないデモではDBの先頭の1体（なければ作成）へ加算する。
    経験値は分数に一本化しているので、勉強時間と同じ育成ロジックを通す。
    """
    if TASK_COMPLETION_XP_MINUTES <= 0:
        return

    character = get_or_create_demo_character(db, for_update=True)
    add_study_minutes_to_character(
        character, TASK_COMPLETION_XP_MINUTES, utc_now()
    )


def _update_task_status(
    db: Session,
    category: str,
    task_id: int,
    done: bool,
) -> Task:
    """タスクの達成状況を変更する。未完了→完了のときだけXPを加算する。"""

    task = db.scalar(
        select(Task).where(Task.id == task_id, Task.category == category)
    )
    if task is None:
        raise HTTPException(
            status_code=404,
            detail=f"{category} task not found",
        )

    newly_completed = done and not task.done
    task.done = done
    if newly_completed:
        _award_task_completion_xp(db)
    db.commit()
    db.refresh(task)
    return task


@router.post(
    "/study/{task_id}/status",
    response_model=StudyTask,
)
def update_study_task_status(
    task_id: int,
    update: TaskStatusUpdate,
    db: Session = Depends(get_db),
) -> StudyTask:
    """勉強タスクの達成状況を変更する。

    未完了から完了に変わったときだけ、キャラへ経験値を加算する。
    （完了→未完了に戻したり、既に完了済みのタスクを再送しても加算しない。）
    """

    return _to_study_task(_update_task_status(db, "study", task_id, update.done))


@router.post(
    "/exercise/{task_id}/status",
    response_model=ExerciseTask,
)
def update_exercise_task_status(
    task_id: int,
    update: TaskStatusUpdate,
    db: Session = Depends(get_db),
) -> ExerciseTask:
    """運動タスクの達成状況を変更する。

    未完了から完了に変わったときだけ、キャラへ経験値を加算する。
    """

    return _to_exercise_task(
        _update_task_status(db, "exercise", task_id, update.done)
    )


# =========================================================
# デモ用：タスクの完了状態をリセット
# =========================================================


class TaskResetResponse(BaseModel):
    reset_count: int


@router.post(
    "/reset",
    response_model=TaskResetResponse,
    summary="タスクの完了状態をリセット（デモ用）",
)
def reset_tasks(db: Session = Depends(get_db)) -> TaskResetResponse:
    """全タスクの完了状態(done)を未完了へ戻す。

    デモで繰り返しタスク達成を見せるための機能。ログインが無いため
    完了状態は全員共通で、このAPIを叩いたときだけ一括リセットする。
    """

    tasks = list(db.scalars(select(Task)).all())
    count = 0
    for task in tasks:
        if task.done:
            task.done = False
            count += 1
    db.commit()
    return TaskResetResponse(reset_count=count)
