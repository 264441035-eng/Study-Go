# Study-Go

TypeScript フロントエンド (React + Vite) と Python バックエンド (FastAPI) のモノレポ。
`main` へマージすると GitHub Actions が AWS ECS Fargate へ自動デプロイする。

- 公開 URL（ALB）: http://study-go-alb-666742485.ap-northeast-1.elb.amazonaws.com
- リージョン: 東京 (`ap-northeast-1`)　/　AWS アカウント: `926736850971`

## 構成

```
frontend/   React + Vite + TypeScript（ビルド後 nginx で静的配信）
backend/    FastAPI（uvicorn）
infra/      Terraform（VPC / ECR / ALB / ECS Fargate / IAM / GitHub OIDC）
.github/    GitHub Actions（ci.yml = CI / deploy.yml = デプロイ）
```

アクセス経路: `ユーザー → ALB(:80) → ECS Fargate`。ALB がパスでルーティングし、
`/api/*`・`/health` は backend、それ以外は frontend に振り分ける（＝同一オリジン）。

## ローカル開発

### まとめて起動（Docker）

```bash
docker compose up --build
# フロント: http://localhost:8081
# API:      http://localhost:8000/api/hello
# DB管理画面(Adminer): http://localhost:8082
```

フロントの nginx が `/api` をバックエンドへプロキシするため同一オリジンで動作する。

### DBの中身をブラウザで見る（Adminer）

`docker-compose.yml` に含まれる Adminer コンテナ経由で、DB の中身をブラウザで確認できる
（ローカル確認専用で、本番環境（ECS）には含めていない）。

1. `docker compose up -d adminer`（他のサービスも起動していない場合は `db` も併せて起動する）
2. ブラウザで `http://localhost:8082` を開く
3. ログイン画面で以下を入力する
   - システム: `PostgreSQL`
   - サーバ: `db`（未入力でも `ADMINER_DEFAULT_SERVER` によりデフォルトで入る）
   - ユーザ名: `study_go`
   - パスワード: `study_go`
   - データベース: `study_go`
4. ログイン後、左メニューのテーブル一覧（`bases` / `characters` / `todo_items` など）から
   任意のテーブルをクリックすると、データをテーブル形式で閲覧・編集できる。

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

- **`ci.yml`**（Pull Request 時）: `backend` ジョブ（ruff + pytest）と `frontend` ジョブ
  （eslint + `vite build` + vitest）。この 2 ジョブは `main` のブランチ保護で必須化している（後述）。
- **`deploy.yml`**（`main` へ push 時）: 下記フローで backend/frontend を並列デプロイ。

### デプロイの流れ（`deploy.yml`）

```
main へ push
  └─ OIDC で AWS ロール(AWS_ROLE_ARN)を一時 assume（アクセスキー不要）
       └─ ECR ログイン
            └─ Docker build → ECR へ push（タグ = commit SHA と latest）
                 └─ 現行 task definition を取得しイメージだけ差し替えて登録
                      └─ ecs update-service でローリング更新（安定するまで待機）
```

- イメージ更新は CI が担当し、Terraform 側は ECS の `task_definition` 変更を無視する
  （`ignore_changes`）。**インフラ（Terraform）とデプロイ（CI）の責務を分離**している。
- 通常運用では `main` にマージするだけでデプロイされる。手動再実行は Actions の
  `deploy` ワークフローを `Run workflow`（workflow_dispatch）で起動、または
  `gh run rerun <run-id>`。

### 初回セットアップ（インフラ構築とデプロイ有効化）

1. インフラ構築（`infra/README.md` も参照）
   ```bash
   cd infra
   terraform init
   terraform plan
   terraform apply          # VPC/ECR/ALB/ECS/IAM/OIDC を東京に作成（課金発生）
   ```
2. 出力 `github_actions_role_arn` を、リポジトリの
   **Settings → Secrets and variables → Actions** に **`AWS_ROLE_ARN`** として登録
   （CLI: `gh secret set AWS_ROLE_ARN --body "<role-arn>"`）。
3. `main` へ push するとデプロイが走る。初回はイメージ push 後に ECS が healthy になる。

> **注意（GitHub OIDC の subject 形式）**
> この組織は OIDC の `sub` クレームに不変の数値 ID を埋め込む設定になっており、
> 実際の subject は `repo:<owner>@<owner_id>/<repo>@<repo_id>:...` の形になる。
> そのため IAM ロールの信頼ポリシーは通常形式だけでなく **ID 付き形式**も許可している
> （`infra/variables.tf` の `github_sub_claims`）。`Not authorized to perform
> sts:AssumeRoleWithWebIdentity` が出た場合は、CloudTrail の `AssumeRoleWithWebIdentity`
> イベントで実際の `sub` を確認し、`github_sub_claims` を合わせる。

### コストと撤去

ALB + NAT Gateway + Fargate ×2 が常時課金対象（概算で月 $60 前後）。
使わない場合は撤去する:

```bash
cd infra
terraform destroy
```

## ブランチ保護（`main`）

`main` 宛の Pull Request は CI（`backend` / `frontend` ジョブ）が成功しないと
マージできないよう保護している。設定には **リポジトリの admin 権限が必要**。

`gh` で設定する例（admin 権限のあるアカウントで実行）:

```bash
gh api -X PUT repos/264441035-eng/Study-Go/branches/main/protection \
  --input - <<'JSON'
{
  "required_status_checks": {
    "strict": true,
    "contexts": ["backend", "frontend"]
  },
  "enforce_admins": false,
  "required_pull_request_reviews": null,
  "restrictions": null
}
JSON
```

- `contexts` は CI の 2 ジョブ名。`strict: true` は「main に追随済みのブランチのみマージ可」。
- 画面から行う場合: **Settings → Branches → Add branch ruleset / protection rule** で
  `main` に対し *Require status checks to pass* を有効化し、`backend` と `frontend` を選択。
