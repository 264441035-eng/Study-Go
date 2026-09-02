# AI Tutor 手動デプロイ手順（学生トライアル復旧用）

`main` への push で `deploy.yml` が走ると、frontend は **`main` の素の画面**（チャットページ無し）で上書きされ、
学生配布 URL `#/chat` が開けなくなる。復旧するには、チャットページを含む `feat/ai-tutor-phase1` の
frontend を手動でビルド & デプロイし直す。以下はそのランブック。

- AWS アカウント: **docomohack (926736850971) / ap-northeast-1** — 全コマンド `AWS_PROFILE=docomohack`
- ECR レジストリ: `926736850971.dkr.ecr.ap-northeast-1.amazonaws.com`
- クラスタ: `study-go-cluster`
- ALB: `study-go-alb-666742485.ap-northeast-1.elb.amazonaws.com`

## 前提の整理（なぜ frontend だけ手動なのか）

- **backend**: `main` push の CI が rev7（`DATABASE_URL` secret を持つ task def）を土台に新イメージを載せて更新するため、
  DB 配線は維持され自動で healthy のまま。**手動不要**。
- **ai-tutor サービス** (`study-go-ai-tutor`): `main` の deploy matrix に含まれない（`feat/ai-tutor-phase1` 限定）ため、
  `main` push では**一切触られない**。動き続ける。イメージを変えたい時だけ再 push（末尾の任意手順）。
- **frontend**: `main` push で素の画面に上書きされる**唯一のサービス**。→ 下記で復旧する。

## 復旧手順（frontend を chat 版に戻す）

```bash
export AWS_PROFILE=docomohack
REG=926736850971.dkr.ecr.ap-northeast-1.amazonaws.com

# 1. チャットページを含むブランチへ
git checkout feat/ai-tutor-phase1

# 2. ECR ログイン
aws ecr get-login-password --region ap-northeast-1 \
  | docker login --username AWS --password-stdin "$REG"

# 3. frontend を amd64 でビルドして push（Fargate は X86_64 / VITE_AI_TUTOR_URL は同一オリジン配信のため空）
cd frontend
docker buildx build --platform linux/amd64 \
  --build-arg VITE_AI_TUTOR_URL="" \
  -t "$REG/study-go-frontend:latest" --push .
cd ..
```

### 4. `:latest` を指す task def を登録して service を更新

CI 後の frontend task def は commit SHA のイメージを指しているので、`:latest` を指す新リビジョンを作り直してから更新する。

```bash
export AWS_PROFILE=docomohack
REG=926736850971.dkr.ecr.ap-northeast-1.amazonaws.com

# 現行 task def を取得し、登録不可フィールドを除去 & image を :latest に差し替えて新リビジョン登録
aws ecs describe-task-definition --task-definition study-go-frontend \
  --query 'taskDefinition' --output json > /tmp/fe-td.json

python3 - <<'PY'
import json
td = json.load(open("/tmp/fe-td.json"))
for k in ["taskDefinitionArn","revision","status","requiresAttributes",
          "compatibilities","registeredAt","registeredBy"]:
    td.pop(k, None)
for c in td["containerDefinitions"]:
    if c["name"] == "frontend":
        c["image"] = c["image"].rsplit(":",1)[0] + ":latest"
json.dump(td, open("/tmp/fe-td-new.json","w"))
PY

NEW_ARN=$(aws ecs register-task-definition --cli-input-json file:///tmp/fe-td-new.json \
  --query 'taskDefinition.taskDefinitionArn' --output text)

aws ecs update-service --cluster study-go-cluster --service study-go-frontend \
  --task-definition "$NEW_ARN"
```

> 補足: 現行 task def が既に `:latest` を指しているなら、上記の代わりに
> `aws ecs update-service --cluster study-go-cluster --service study-go-frontend --force-new-deployment` だけで良い。

### 5. 反映確認

```bash
export AWS_PROFILE=docomohack
aws ecs describe-services --cluster study-go-cluster --services study-go-frontend \
  --query 'services[0].deployments[].{status:status,desired:desiredCount,running:runningCount,rollout:rolloutState}' --output table
# rolloutState が COMPLETED / running=1 になれば OK
```

ブラウザで `http://study-go-alb-666742485.ap-northeast-1.elb.amazonaws.com/#/chat?token=<jwt>` を開き、
チャット画面（「会話を始める」ボタン）が出れば復旧完了。`/`（トップ）は `main` と同じ素の画面のまま。

## 学生トークンの発行

JWT_SECRET は SSM SecureString（`/study-go/ai-tutor/jwt-secret` 相当）または `terraform output` から取得。

```bash
export AWS_PROFILE=docomohack
SECRET=$(cd infra && /tmp/terraform output -raw ai_tutor_jwt_secret)   # ← state に両ファイルが揃っているツリーで
BASE=http://study-go-alb-666742485.ap-northeast-1.elb.amazonaws.com

cd ai-tutor-service
JWT_SECRET="$SECRET" python -m scripts.issue_student_tokens \
  --base-url "$BASE" --days 30 student01
# 出力: student01<TAB>http://.../#/chat?token=eyJ...  ← この URL を学生に配布
```

## （任意）ai-tutor サービス自体のイメージ更新

会話ロジック等を変えた時だけ。frontend と違い `main` push では上書きされない。

```bash
export AWS_PROFILE=docomohack
REG=926736850971.dkr.ecr.ap-northeast-1.amazonaws.com
cd ai-tutor-service
docker buildx build --platform linux/amd64 -t "$REG/study-go-ai-tutor:latest" --push .
aws ecs update-service --cluster study-go-cluster --service study-go-ai-tutor --force-new-deployment
```

## Terraform の落とし穴（重要）

infra の Terraform state は**このMac上のローカル**（`infra/terraform.tfstate`）で、`feat/ai-tutor-phase1`（`ai_tutor.tf`）と
`fix/backend-rds-deploy`（`database.tf`）の**両方のリソースを保持**している。
片方のブランチ単独で `terraform apply` すると相手のリソースを destroy しようとするため、
**apply は必ず両ファイルが揃ったツリー（= 両 PR マージ後の main）から**行うこと。
このランブックの手順は Terraform を一切使わない（Docker + ECS API のみ）ので安全。
