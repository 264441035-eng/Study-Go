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

## CI / デプロイ

GitHub Actions で以下を実行する（`.github/workflows/`）。

- **`ci.yml`**（Pull Request 時）: backend の ruff/pytest、frontend の eslint/build/vitest
- **`deploy.yml`**（main へ push 時）: OIDC で AWS を assume → Docker イメージを ECR に push
  → 現行 task definition のイメージだけ差し替えて ECS サービスをローリング更新

リージョンは東京 (`ap-northeast-1`)。

### 事前設定（デプロイに必要）

1. `infra/` を `terraform apply` してインフラと OIDC ロールを作成
2. 出力された `github_actions_role_arn` を、リポジトリの
   **Settings → Secrets and variables → Actions** に `AWS_ROLE_ARN` として登録
