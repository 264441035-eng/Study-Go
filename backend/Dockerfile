FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
# Alembic のマイグレーション定義。デプロイ時の one-off タスクで
# `alembic upgrade head` を実行するために同梱する。
COPY alembic.ini ./alembic.ini
COPY migrations ./migrations

EXPOSE 8000
# 起動は uvicorn のみ。スキーマ初期化/マイグレーションは起動から切り離し、
# デプロイ時に one-off タスクとして `alembic upgrade head` を明示実行する。
# これにより DB 障害/設定ミスでサービス全体がクラッシュループするのを防ぐ。
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
