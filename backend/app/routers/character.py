"""キャラクターの作成・取得・育成を扱うAPIと計算ロジック。"""

import os
from bisect import bisect_right
from datetime import date, datetime, timedelta, timezone
from math import ceil
from uuid import UUID
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Character
from app.schemas import CharacterCreate, CharacterOut, StudyRequest

router = APIRouter(prefix="/api/characters", tags=["character"])

# 追加設定: 初期値は短時間で確認するデモ用。本番では環境変数で大きくする。
MAX_LEVEL = 100
MAX_LEVEL_LOSS_FROM_HIGHEST = 10
EVOLUTION_LEVELS = (10, 30, 60, 100)
BASE_LEVEL_MINUTES = int(os.getenv("CHARACTER_BASE_LEVEL_MINUTES", "1"))
LEVEL_GROWTH_MINUTES = int(os.getenv("CHARACTER_LEVEL_GROWTH_MINUTES", "1"))
STUDY_TIMEZONE = ZoneInfo("Asia/Tokyo")


# 追加関数: テストで差し替えやすいよう、現在時刻の取得を集約する。
def utc_now() -> datetime:
    """DB保存と時間計算に使う、タイムゾーン付きUTC現在時刻を返す。"""
    return datetime.now(timezone.utc)


# 追加関数: 分を表示用の「時間:分」へ変換する。
def format_minutes(total_minutes: int) -> str:
    """分数を、24時間を超えても使える「時間:分」形式へ変換する。

    例: 90分は ``01:30``、1505分は ``25:05`` になる。
    """
    hours, minutes = divmod(total_minutes, 60)
    return f"{hours:02}:{minutes:02}"


# 追加関数: 現在レベルから次レベルまでに必要な勉強時間を返す。
def required_minutes_for_next_level(level: int) -> int:
    """指定レベルから次レベルへ進むために必要な勉強時間（分）を返す。

    10レベルごとに必要時間が増える。環境変数の初期値はデモ用で、
    本番ではCHARACTER_BASE_LEVEL_MINUTESなどを大きく設定する。
    """
    return BASE_LEVEL_MINUTES + LEVEL_GROWTH_MINUTES * ((level - 1) // 10)


# 追加関数: 各レベルに到達する累積必要時間リストを一度だけ作る。
def build_level_thresholds() -> list[int]:
    """レベル1～100へ到達するための累積必要時間一覧を作る。

    リストのindex 0がレベル1、index 1がレベル2への到達時間に対応する。
    """
    thresholds = [0]
    total_minutes = 0
    for level in range(1, MAX_LEVEL):
        total_minutes += required_minutes_for_next_level(level)
        thresholds.append(total_minutes)
    return thresholds


LEVEL_THRESHOLDS = build_level_thresholds()


# 追加関数: 有効勉強時間から現在レベルと次レベルまでの残り時間を返す。
def calculate_level_progress(effective_minutes: int) -> tuple[int, int]:
    """有効勉強時間から現在レベルと次レベルまでの残り時間を返す。

    戻り値は ``(level, remaining_minutes)``。最大レベル100では残り時間を0とする。
    """
    level = min(bisect_right(LEVEL_THRESHOLDS, effective_minutes), MAX_LEVEL)
    if level == MAX_LEVEL:
        return MAX_LEVEL, 0
    return level, LEVEL_THRESHOLDS[level] - effective_minutes


# 追加関数: レベルから進化段階0～4を返す。
def evolution_stage_for_level(level: int) -> int:
    """レベル10・30・60・100を境界として進化段階0～4を返す。"""
    return bisect_right(EVOLUTION_LEVELS, level)


# 追加関数: 基準時間から派生する状態をまとめて更新し、値の矛盾を防ぐ。
# 過去の最高レベルを更新したときだけ、最低保証レベルも「最高-10」に更新する。
def refresh_character_progress(character: Character) -> None:
    """勉強・ペナルティ時間からキャラクターの派生状態を一括更新する。

    有効勉強時間、現在レベル、最高レベル、最低保証レベル、進化段階、
    次レベルまでの残り時間を更新する。最高レベルはペナルティでは下げない。
    """
    effective_minutes = max(
        character.total_study_minutes - character.total_penalty_minutes, 0
    )
    level, remaining_minutes = calculate_level_progress(effective_minutes)
    character.effective_study_minutes = effective_minutes
    character.level = level
    if level > character.highest_level:
        character.highest_level = level
        character.minimum_level = max(
            character.highest_level - MAX_LEVEL_LOSS_FROM_HIGHEST, 1
        )
    character.evolution_stage = evolution_stage_for_level(level)
    character.remaining_minutes_to_next_level = remaining_minutes


# 追加関数: 前レベルから現在レベルまでに必要な時間の1/4を返す。
# 時間は整数の「分」で保持するため、1/4で生じた端数は切り上げる。
def penalty_minutes_for_level(level: int) -> int:
    """未学習日1日分の基本ペナルティ時間（分）を返す。

    前レベルから現在レベルまでの必要時間の1/4を分単位で切り上げる。
    レベル1には、それより下のレベルがないため0を返す。
    """
    if level <= 1:
        return 0
    minutes_required_to_reach_current_level = required_minutes_for_next_level(level - 1)
    return ceil(minutes_required_to_reach_current_level / 4)


# 追加関数: 最低保証レベルを維持できる、追加可能なペナルティ時間Pを返す。
# P = 現在の有効勉強時間 - 最低保証レベルへの到達に必要な累積時間
def maximum_additional_penalty_minutes(character: Character) -> int:
    """最低保証レベルを下回らずに追加できるペナルティ時間Pを返す。"""
    minimum_effective_minutes = LEVEL_THRESHOLDS[character.minimum_level - 1]
    return max(character.effective_study_minutes - minimum_effective_minutes, 0)


# 追加関数: 最低保証レベルまでの残り時間Pを考慮して1回分を加算する。
def apply_one_penalty(character: Character) -> int:
    """未学習日1日分のペナルティを適用し、実際に加算した分数を返す。

    基本ペナルティと追加可能時間Pの小さい方だけを加算するため、
    何回呼び出しても最低保証レベルを下回らない。
    """
    base_penalty = penalty_minutes_for_level(character.level)
    maximum_penalty = maximum_additional_penalty_minutes(character)
    applied_penalty = min(base_penalty, maximum_penalty)
    character.total_penalty_minutes += applied_penalty
    refresh_character_progress(character)
    return applied_penalty


# 追加関数: 日時を勉強日判定に使う日本時間の日付へ変換する。
def study_date(value: datetime) -> date:
    """日時を日本時間へ変換し、未学習日判定に使う日付を返す。"""
    return value.astimezone(STUDY_TIMEZONE).date()


# 追加関数: 最終勉強日と現在日の間にある未適用日を、1日1回として反映する。
# 例: 12日に勉強して15日に判定した場合、13日と14日の2回分を適用する。
# 各回で最低保証レベルまでの残り時間Pを再計算するため、何回適用しても下回らない。
def apply_inactivity_penalty(character: Character, now: datetime) -> None:
    """最終勉強日と現在日の間にある未学習日へペナルティを適用する。

    12日に勉強して15日に呼ばれた場合は、13日と14日の2回分を適用する。
    penalty_applied_throughにより、同じ日への重複適用を防ぐ。
    """
    if character.last_studied_at is None:
        return

    last_study_date = study_date(character.last_studied_at)
    first_unapplied_date = last_study_date + timedelta(days=1)
    if character.penalty_applied_through is not None:
        first_unapplied_date = max(
            first_unapplied_date,
            character.penalty_applied_through + timedelta(days=1),
        )

    last_inactive_date = study_date(now) - timedelta(days=1)
    penalty_date = first_unapplied_date
    while penalty_date <= last_inactive_date:
        apply_one_penalty(character)
        character.penalty_applied_through = penalty_date
        penalty_date += timedelta(days=1)


# 追加関数: 検索と404処理を各エンドポイントで重複させない。
def find_character_or_404(character_id: UUID, db: Session) -> Character:
    """UUID主キーでキャラクターを取得し、存在しなければHTTP 404を返す。"""
    character = db.get(Character, character_id)
    if character is None:
        raise HTTPException(status_code=404, detail="Character not found")
    return character


# 追加関数: ログインのないデモで使用する1体を取得し、なければ作成する。
def get_or_create_demo_character(
    db: Session, *, for_update: bool = False
) -> Character:
    """DBの先頭のキャラクターを取得し、存在しなければ初期状態で作成する。

    ``for_update=True`` の場合は既存行をロックして、同時更新による
    累計勉強時間の消失を防ぐ。トランザクションの確定は呼び出し元に任せる。
    """
    statement = select(Character).order_by(Character.id).limit(1)
    if for_update:
        statement = statement.with_for_update()

    character = db.scalar(statement)
    if character is not None:
        return character

    character = Character(
        name="Demo Character",
        total_study_minutes=0,
        total_penalty_minutes=0,
        effective_study_minutes=0,
        level=1,
        highest_level=1,
        minimum_level=1,
        evolution_stage=0,
        remaining_minutes_to_next_level=0,
        last_studied_at=None,
        penalty_applied_through=None,
    )
    refresh_character_progress(character)
    db.add(character)
    db.flush()
    return character


# 追加関数: Characterへの勉強時間加算と育成状態更新を一か所に集約する。
def add_study_minutes_to_character(
    character: Character, minutes: int, now: datetime
) -> None:
    """正の勉強時間（分）を加算し、ペナルティと育成状態を更新する。

    DBへのコミットは行わず、Character APIやTask APIなどの呼び出し元が
    ほかのDB更新とまとめてトランザクションを確定できるようにする。
    """
    if minutes <= 0:
        raise ValueError("Study minutes must be greater than zero")

    apply_inactivity_penalty(character, now)
    character.total_study_minutes += minutes
    refresh_character_progress(character)
    character.last_studied_at = now
    character.penalty_applied_through = study_date(now)


# 追加関数: キャラクターを作成直後と同じ初期状態へ戻す。
# デモで何度もレベルアップを見せるため、勉強・ペナルティ・育成状態を一括で初期化する。
def reset_character_progress(character: Character) -> None:
    """キャラクターの勉強時間・ペナルティ・育成状態を初期状態へ戻す。

    create_characterの初期化と同じ値へ戻し、最後にrefresh_character_progressで
    派生状態を再計算する。DBへのコミットは呼び出し元に任せる。
    """
    character.total_study_minutes = 0
    character.total_penalty_minutes = 0
    character.effective_study_minutes = 0
    character.level = 1
    character.highest_level = 1
    character.minimum_level = 1
    character.evolution_stage = 0
    character.remaining_minutes_to_next_level = 0
    character.last_studied_at = None
    character.penalty_applied_through = None
    refresh_character_progress(character)


# 追加関数: 保存状態を表示用時間を含むAPIレスポンスへ変換する。
def to_character_out(character: Character) -> CharacterOut:
    """DBモデルを表示用時間付きのAPIレスポンスへ変換する。

    last_studied_atはDB保存時の時刻から日本時間へ変換して返す。
    """
    last_studied_at = character.last_studied_at
    if last_studied_at is not None:
        last_studied_at = last_studied_at.astimezone(STUDY_TIMEZONE)
    return CharacterOut(
        id=character.id,
        name=character.name,
        total_study_minutes=character.total_study_minutes,
        total_penalty_minutes=character.total_penalty_minutes,
        effective_study_minutes=character.effective_study_minutes,
        level=character.level,
        highest_level=character.highest_level,
        minimum_level=character.minimum_level,
        evolution_stage=character.evolution_stage,
        remaining_minutes_to_next_level=character.remaining_minutes_to_next_level,
        last_studied_at=last_studied_at,
        penalty_applied_through=character.penalty_applied_through,
        total_study_time=format_minutes(character.total_study_minutes),
        total_penalty_time=format_minutes(character.total_penalty_minutes),
        effective_study_time=format_minutes(character.effective_study_minutes),
        remaining_time_to_next_level=format_minutes(
            character.remaining_minutes_to_next_level
        ),
    )


@router.get("", summary="キャラクター一覧を取得")
def list_characters(db: Session = Depends(get_db)) -> list[CharacterOut]:
    """保存されている全キャラクターを返す。

    入力はない。取得日の前日までに未適用の日があれば、ペナルティをDBへ反映してから
    各キャラクターの育成状態と表示用時間を返す。
    """
    now = utc_now()
    characters = list(db.scalars(select(Character)).all())
    for character in characters:
        apply_inactivity_penalty(character, now)
    db.commit()
    return [to_character_out(character) for character in characters]


@router.get("/{character_id}", summary="キャラクターを取得")
def get_character(character_id: UUID, db: Session = Depends(get_db)) -> CharacterOut:
    """指定したキャラクターを返す。

    - **入力**: URLの ``character_id`` に作成時に発行されたUUIDを指定する。
    - **出力**: 現在の育成状態と「時間:分」形式の表示値。
    - **404**: 指定したUUIDのキャラクターが存在しない場合。

    未適用の未学習日があれば、ペナルティをDBへ反映してから返す。
    """
    character = find_character_or_404(character_id, db)
    apply_inactivity_penalty(character, utc_now())
    db.commit()
    return to_character_out(character)


@router.post("", status_code=201, summary="キャラクターを作成")
def create_character(
    character: CharacterCreate, db: Session = Depends(get_db)
) -> CharacterOut:
    """名前を受け取り、初期状態のキャラクターをDBへ作成する。

    - **入力JSON**: ``{"name": "Hero"}``
    - **出力**: 自動生成されたUUID、レベル1の育成状態、表示用時間。
    - **422**: 名前が空、または50文字を超える場合。

    勉強時間やレベルは入力させず、すべてサーバー側の初期値と計算結果を保存する。
    """
    created = Character(
        name=character.name,
        total_study_minutes=0,
        total_penalty_minutes=0,
        effective_study_minutes=0,
        level=1,
        highest_level=1,
        minimum_level=1,
        evolution_stage=0,
        remaining_minutes_to_next_level=0,
        last_studied_at=None,
        penalty_applied_through=None,
    )
    refresh_character_progress(created)
    db.add(created)
    db.commit()
    db.refresh(created)
    return to_character_out(created)


@router.post("/initialize", summary="デモ用キャラクターを取得または作成")
def initialize_demo_character(db: Session = Depends(get_db)) -> UUID:
    """デモで使用する1体のキャラクターIDを返す。

    - DBにキャラクターが1体以上あれば、先頭のキャラクターIDを返す。
    - DBにキャラクターがなければ、名前が ``Demo Character`` のキャラクターを作成し、
      作成されたキャラクターIDを返す。
    - **出力**: キャラクターIDのUUID値。

    ログインのないデモ版で、ホーム画面から使用するキャラクターを決定するためのAPI。
    """
    character = get_or_create_demo_character(db)
    db.commit()
    return character.id


# 追加エンドポイント: 勉強時間を登録して育成状態を更新する。
@router.post("/{character_id}/study", summary="勉強時間を登録")
def record_study(
    character_id: UUID,
    study: StudyRequest,
    db: Session = Depends(get_db),
) -> CharacterOut:
    """指定キャラクターへ勉強時間を加算し、更新後の育成状態を返す。

    - **入力URL**: ``character_id`` にキャラクターのUUIDを指定する。
    - **入力JSON**: ``{"minutes": 30}`` のように正の分数を指定する。
    - **出力**: ペナルティと今回の勉強を反映した最新の育成状態。
    - **404**: 指定したキャラクターが存在しない場合。
    - **422**: minutesが0以下、または整数でない場合。

    同時登録による勉強時間の消失を防ぐため、更新中は対象DB行をロックする。
    """
    character = db.scalar(
        select(Character).where(Character.id == character_id).with_for_update()
    )
    if character is None:
        raise HTTPException(status_code=404, detail="Character not found")
    add_study_minutes_to_character(character, study.minutes, utc_now())

    db.commit()
    db.refresh(character)

    # 表示用の時間を含むAPIレスポンスへ変換して返す。
    return to_character_out(character)


# 追加エンドポイント: デモ用にキャラクターのレベルを初期状態へリセットする。
@router.post("/{character_id}/reset", summary="キャラクターのレベルをリセット")
def reset_character(
    character_id: UUID,
    db: Session = Depends(get_db),
) -> CharacterOut:
    """指定キャラクターの勉強時間・ペナルティ・レベルを初期状態へ戻す。

    - **入力URL**: ``character_id`` にキャラクターのUUIDを指定する。
    - **出力**: リセット後のレベル1の育成状態と表示用時間。
    - **404**: 指定したキャラクターが存在しない場合。

    デモで繰り返しレベルアップを見せるための機能。同時更新による不整合を防ぐため、
    更新中は対象DB行をロックする。
    """
    character = db.scalar(
        select(Character).where(Character.id == character_id).with_for_update()
    )
    if character is None:
        raise HTTPException(status_code=404, detail="Character not found")
    reset_character_progress(character)

    db.commit()
    db.refresh(character)

    return to_character_out(character)
