"""既製タスクの初期データ（単一の定義元）。

このリストを唯一の出典として、
- Alembic マイグレーション（0003）が本番/新規DBへ投入し、
- テストが SQLite へ同じ行を投入する。
ことで、投入経路による差異を防ぐ。

各要素は models.Task の列にそのまま対応する。base_categories は
カンマ区切り文字列（空文字＝どの拠点でも表示）。completion_mode は
"auto_time" / "manual" / "external"。
"""

# 勉強=1〜、運動=101〜 で採番（フロントは id を数値でURLに使う）。
DEFAULT_TASKS: list[dict] = [
    # --- 勉強 (study) ---
    {
        "id": 1,
        "category": "study",
        "title": "30秒勉強する（デモ）",
        "minute": 0.5,
        "required_level": 1,
        "base_categories": "",
        "completion_mode": "auto_time",
    },
    {
        "id": 2,
        "category": "study",
        "title": "AIにやったことを説明する",
        "minute": None,
        "required_level": 2,
        "base_categories": "",
        "completion_mode": "external",
    },
    {
        "id": 3,
        "category": "study",
        "title": "AIの問題に答える",
        "minute": None,
        "required_level": 3,
        "base_categories": "",
        "completion_mode": "external",
    },
    {
        "id": 4,
        "category": "study",
        "title": "5分間集中して勉強する",
        "minute": 5.0,
        "required_level": 1,
        "base_categories": "",
        "completion_mode": "auto_time",
    },
    {
        "id": 5,
        "category": "study",
        "title": "参考書を1ページ読む",
        "minute": None,
        "required_level": 1,
        "base_categories": "",
        "completion_mode": "manual",
    },
    # --- 運動 (exercise) ---
    {
        "id": 101,
        "category": "exercise",
        "title": "拠点まで徒歩で移動する",
        "minute": None,
        "required_level": 1,
        "base_categories": "",
        "completion_mode": "external",
    },
    {
        "id": 102,
        "category": "exercise",
        "title": "散歩する",
        "minute": None,
        "required_level": 1,
        "base_categories": "",
        "completion_mode": "manual",
    },
    {
        "id": 103,
        "category": "exercise",
        "title": "スクワットする",
        "minute": None,
        "required_level": 2,
        "base_categories": "",
        "completion_mode": "manual",
    },
    {
        "id": 104,
        "category": "exercise",
        "title": "ストレッチをする",
        "minute": None,
        "required_level": 1,
        "base_categories": "",
        "completion_mode": "manual",
    },
    {
        "id": 105,
        "category": "exercise",
        "title": "階段を使う",
        "minute": None,
        "required_level": 1,
        "base_categories": "",
        "completion_mode": "manual",
    },
]
