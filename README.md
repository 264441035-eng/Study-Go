# Study-Go

TypeScript フロントエンド (React + Vite) と Python バックエンド (FastAPI) のモノレポ。
main へマージすると GitHub Actions で AWS ECS Fargate へデプロイする構成を目指す。

## 構成

```
frontend/   React + Vite + TypeScript（ビルド後 nginx で配信）
backend/    FastAPI（uvicorn）
infra/      Terraform（VPC / ECR / ALB / ECS Fargate）※作成予定
.github/    GitHub Actions（CI / デプロイ）※作成予定
```

## ローカル開発

### まとめて起動（Docker）

```bash
docker compose up --build
# フロント: http://localhost:8081
# API:      http://localhost:8000/api/hello
```

フロントの nginx が `/api` をバックエンドへプロキシするため同一オリジンで動作する。

### 個別に起動

バックエンド:

```bash
cd backend
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements-dev.txt
uvicorn app.main:app --reload      # http://localhost:8000
pytest                              # テスト
```

フロントエンド:

```bash
cd frontend
npm install
npm run dev                         # http://localhost:5173
npm run build                       # 型チェック + 本番ビルド
```

## デプロイ（予定）

main ブランチへのマージで GitHub Actions が起動し、
Docker イメージを ECR に push → ECS サービスをローリング更新する。
リージョンは東京 (`ap-northeast-1`)。
