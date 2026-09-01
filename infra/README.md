# infra — Terraform (AWS ECS Fargate)

東京リージョン (`ap-northeast-1`) に以下を構築する。

```
VPC (2AZ, public/private subnet, NAT×1)
 ├─ ECR ×2            (backend / frontend イメージ)
 ├─ ALB (HTTP:80)
 │    ├─ /api/*, /health → backend target group
 │    └─ その他          → frontend target group
 ├─ ECS Cluster (Fargate)
 │    ├─ backend service
 │    └─ frontend service
 └─ IAM
      ├─ ECS task execution / task role
      └─ GitHub Actions 用 OIDC ロール（デプロイ権限）
```

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
- 破棄する場合: `terraform destroy`
