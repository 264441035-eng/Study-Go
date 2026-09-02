# infra — Terraform (AWS ECS Fargate)

東京リージョン (`ap-northeast-1`) に以下を構築する。

```
VPC (2AZ, public/private subnet, NAT×1)
 ├─ ECR ×3            (backend / frontend / ai-tutor イメージ)
 ├─ ALB (HTTP:80)
 │    ├─ /sessions*      → ai-tutor target group   (priority 90)
 │    ├─ /api/*, /health → backend target group     (priority 100)
 │    └─ その他          → frontend target group     (default)
 ├─ ECS Cluster (Fargate)
 │    ├─ backend service
 │    ├─ frontend service
 │    └─ ai-tutor service   (LLM_MODE=bedrock / DATABASE_MODE=aws / APP_ENV=production)
 ├─ DynamoDB ×2       (ai-tutor-sessions [GSI1+TTL] / ai-tutor-student-models)
 ├─ SSM SecureString  (/study-go/ai-tutor/jwt-secret … 学生トークン署名鍵)
 └─ IAM
      ├─ ECS task execution / task role
      ├─ ai-tutor task role（Bedrock InvokeModel + DynamoDB CRUD）
      └─ GitHub Actions 用 OIDC ロール（デプロイ権限）
```

AI Tutor はフロントと同一 ALB オリジンに相乗りするため CORS 不要。フロントは
コンテナビルド時 `VITE_AI_TUTOR_URL=""`（相対）で同一オリジンの `/sessions*` を叩く。

## 前提

- Terraform >= 1.6
- AWS 認証情報（`aws configure` もしくは環境変数）。東京リージョンで操作できる権限。

## 使い方

```bash
cd infra
terraform init
terraform plan     # 作成されるリソースを確認
terraform apply    # 実際に構築（軽微な課金が発生）
```

apply 後に出力される値を使う:

- `alb_dns_name` … アプリ URL（`http://<dns>`）
- `github_actions_role_arn` … GitHub Actions Secrets `AWS_ROLE_ARN` に設定
- `ecr_*_repository_url` … CI の push 先

## 補足

- **初回 apply 時点では ECR にイメージが無いため、ECS タスクは pull に失敗して unhealthy のまま**になる。
  GitHub Actions（またはローカル）から backend/frontend イメージを push して
  サービスを更新すると healthy になる。
- ECS サービスは `task_definition` の変更を `ignore_changes` で無視する設定。
  イメージ更新は CI 側（`aws ecs update-service`）が担当し、Terraform とデプロイの責務を分離している。
- state は初期はローカル保存。リモート化する場合は `backend.tf` のコメントを参照。
  **AI Tutor の JWT シークレットが state に入る**ため、チーム/CI 運用では S3 + SSE の
  リモート state に移行すること。
- 破棄する場合: `terraform destroy`

## AI Tutor のデプロイと学生トークン配布（main マージ前のトライアル）

このブランチから apply → イメージ push → 個人 URL 配布、まで main を触らずに行える。

```bash
# 1) infra を適用（ai-tutor の ECR/ECS/DynamoDB/IAM/ALB ルールを追加）
cd infra
terraform init
terraform plan     # ai-tutor 関連リソースの新規作成のみ（既存は無変更）を確認
terraform apply

# 2) ai-tutor イメージを push（CI か手動）。CI は main push か workflow_dispatch で発火。
#    手動例:
#    aws ecr get-login-password --region ap-northeast-1 | docker login --username AWS --password-stdin <acct>.dkr.ecr.ap-northeast-1.amazonaws.com
#    docker build -t <ecr_ai_tutor_repository_url>:latest ../ai-tutor-service
#    docker push <ecr_ai_tutor_repository_url>:latest
#    aws ecs update-service --cluster study-go-cluster --service study-go-ai-tutor --force-new-deployment

# 3) 学生ごとの配布 URL を発行（本番と同じ署名鍵を使う）
SECRET="$(terraform output -raw ai_tutor_jwt_secret)"
BASE="http://$(terraform output -raw alb_dns_name)"
cd ../ai-tutor-service
JWT_SECRET="$SECRET" python -m scripts.issue_student_tokens \
  --base-url "$BASE" --days 30 student01 student02 student03
# 出力: 各学生の  http://<alb>/#/chat?token=<jwt>  を配布
```

- `/dev/token` は `APP_ENV=production` で無効。学生は配布 URL のトークンのみで利用可。
- コスト上限（`MAX_TURNS` / `MAX_SESSIONS_PER_DAY` / `MAX_MESSAGE_CHARS`）は既定値が効く。
  学生ごとに `user_id` を分けるので日次上限が個人単位で機能する。
