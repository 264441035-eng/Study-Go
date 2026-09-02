FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

EXPOSE 8000
# コンテナ起動時にテーブルを作成してからAPIサーバーを起動する（簡易セットアップ）。
# 本番運用でスキーマ変更が発生する場合はAlembic等のマイグレーションツールへの置き換えを推奨。
CMD ["sh", "-c", "python -c 'from app.database import init_db; init_db()' && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
