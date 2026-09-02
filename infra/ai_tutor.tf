# AI Tutor Service (FastAPI + Bedrock + DynamoDB) を既存 ECS/ALB に相乗りで追加。
#
# ルーティング: 既存 ALB の /sessions* を AI Tutor へ振り分ける。フロントと同一
# オリジンになるため CORS 不要。/health は既存 backend が保持 (TG ヘルスチェックは
# ターゲットへ直接飛ぶのでリスナールールとは無関係)。
# app 本体は DATABASE_MODE=aws / LLM_MODE=bedrock / APP_ENV!=local で動かす
# (APP_ENV!=local で /dev/token は無効化され、配布トークンのみ受理)。

# ---------------- ECR ----------------
resource "aws_ecr_repository" "ai_tutor" {
  name                 = "${var.project}-ai-tutor"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }
}

resource "aws_ecr_lifecycle_policy" "ai_tutor" {
  repository = aws_ecr_repository.ai_tutor.name
  policy     = local.ecr_lifecycle_policy
}

# ---------------- DynamoDB (app の create_tables.py と同一スキーマ) ----------------
resource "aws_dynamodb_table" "sessions" {
  name         = var.ai_tutor_sessions_table
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "PK"
  range_key    = "SK"

  attribute {
    name = "PK"
    type = "S"
  }
  attribute {
    name = "SK"
    type = "S"
  }
  attribute {
    name = "gsi1pk"
    type = "S"
  }
  attribute {
    name = "gsi1sk"
    type = "S"
  }

  global_secondary_index {
    name            = "GSI1"
    hash_key        = "gsi1pk"
    range_key       = "gsi1sk"
    projection_type = "KEYS_ONLY"
  }

  ttl {
    attribute_name = "ttl"
    enabled        = true
  }
}

resource "aws_dynamodb_table" "student_models" {
  name         = var.ai_tutor_student_models_table
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "PK"
  range_key    = "SK"

  attribute {
    name = "PK"
    type = "S"
  }
  attribute {
    name = "SK"
    type = "S"
  }
}

# ---------------- JWT シークレット (SSM SecureString) ----------------
# 学生配布トークンの署名鍵。ランダム生成し SSM に格納、コンテナは secrets で参照。
# 値は state に入るため、リモート state は暗号化 (S3 + SSE) 前提。
# トークン発行時は `terraform output -raw ai_tutor_jwt_secret` で取得して
#   JWT_SECRET=<値> python -m scripts.issue_student_tokens ...
resource "random_password" "jwt_secret" {
  length  = 48
  special = false
}

resource "aws_ssm_parameter" "jwt_secret" {
  name  = "/${var.project}/ai-tutor/jwt-secret"
  type  = "SecureString"
  value = random_password.jwt_secret.result
}

# 実行ロールが SecureString を読めるように (AWS 管理キーなので kms:Decrypt は不要)
data "aws_iam_policy_document" "ai_tutor_execution_ssm" {
  statement {
    actions   = ["ssm:GetParameters"]
    resources = [aws_ssm_parameter.jwt_secret.arn]
  }
}

resource "aws_iam_role_policy" "ai_tutor_execution_ssm" {
  name   = "${var.project}-ai-tutor-exec-ssm"
  role   = aws_iam_role.ecs_task_execution.id
  policy = data.aws_iam_policy_document.ai_tutor_execution_ssm.json
}

# ---------------- タスクロール (Bedrock + DynamoDB) ----------------
resource "aws_iam_role" "ai_tutor_task" {
  name               = "${var.project}-ai-tutor-task"
  assume_role_policy = data.aws_iam_policy_document.ecs_assume.json
}

data "aws_iam_policy_document" "ai_tutor_task" {
  # Bedrock: Anthropic Claude を jp.* Inference Profile 経由で呼ぶ。
  # クロスリージョン Profile は各リージョンの foundation-model への権限も要る。
  statement {
    sid     = "BedrockInvoke"
    actions = ["bedrock:InvokeModel", "bedrock:InvokeModelWithResponseStream"]
    resources = [
      "arn:aws:bedrock:*:${data.aws_caller_identity.current.account_id}:inference-profile/jp.anthropic.*",
      "arn:aws:bedrock:*::foundation-model/anthropic.claude-*",
    ]
  }

  statement {
    sid = "DynamoDbCrud"
    actions = [
      "dynamodb:GetItem",
      "dynamodb:BatchGetItem",
      "dynamodb:Query",
      "dynamodb:PutItem",
      "dynamodb:UpdateItem",
      "dynamodb:DeleteItem",
      "dynamodb:BatchWriteItem",
    ]
    resources = [
      aws_dynamodb_table.sessions.arn,
      "${aws_dynamodb_table.sessions.arn}/index/*",
      aws_dynamodb_table.student_models.arn,
    ]
  }
}

resource "aws_iam_role_policy" "ai_tutor_task" {
  name   = "${var.project}-ai-tutor-task"
  role   = aws_iam_role.ai_tutor_task.id
  policy = data.aws_iam_policy_document.ai_tutor_task.json
}

# ---------------- ログ / タスク定義 / サービス ----------------
resource "aws_cloudwatch_log_group" "ai_tutor" {
  name              = "/ecs/${var.project}-ai-tutor"
  retention_in_days = 14
}

resource "aws_ecs_task_definition" "ai_tutor" {
  family                   = "${var.project}-ai-tutor"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = var.ai_tutor_cpu
  memory                   = var.ai_tutor_memory
  execution_role_arn       = aws_iam_role.ecs_task_execution.arn
  task_role_arn            = aws_iam_role.ai_tutor_task.arn

  container_definitions = jsonencode([
    {
      name      = "ai-tutor"
      image     = "${aws_ecr_repository.ai_tutor.repository_url}:${var.image_tag}"
      essential = true
      portMappings = [
        { containerPort = var.backend_container_port, protocol = "tcp" }
      ]
      environment = [
        { name = "APP_ENV", value = var.ai_tutor_app_env },
        { name = "LLM_MODE", value = "bedrock" },
        { name = "DATABASE_MODE", value = "aws" },
        { name = "BACKEND_MODE", value = "mock" },
        { name = "BEDROCK_REGION", value = var.aws_region },
        { name = "AWS_REGION", value = var.aws_region },
        { name = "CONVERSATION_MODEL_ID", value = var.ai_tutor_conversation_model_id },
        { name = "ASSESSMENT_MODEL_ID", value = var.ai_tutor_assessment_model_id },
        { name = "SESSIONS_TABLE", value = aws_dynamodb_table.sessions.name },
        { name = "STUDENT_MODELS_TABLE", value = aws_dynamodb_table.student_models.name },
        # フロントと同一 ALB オリジンなので実質不要だが明示。
        { name = "CORS_ORIGINS", value = "http://${aws_lb.main.dns_name}" },
      ]
      secrets = [
        { name = "JWT_SECRET", valueFrom = aws_ssm_parameter.jwt_secret.arn }
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.ai_tutor.name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "ai-tutor"
        }
      }
    }
  ])
}

resource "aws_lb_target_group" "ai_tutor" {
  name        = "${var.project}-ai-tutor-tg"
  port        = var.backend_container_port
  protocol    = "HTTP"
  vpc_id      = aws_vpc.main.id
  target_type = "ip"

  health_check {
    path                = "/health"
    matcher             = "200"
    healthy_threshold   = 2
    unhealthy_threshold = 3
    interval            = 30
    timeout             = 5
  }
}

# /sessions* を AI Tutor へ (既存 backend の /api*・/health より前に評価)
resource "aws_lb_listener_rule" "ai_tutor" {
  listener_arn = aws_lb_listener.http.arn
  priority     = 90

  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.ai_tutor.arn
  }

  condition {
    path_pattern {
      values = ["/sessions", "/sessions/*"]
    }
  }
}

resource "aws_ecs_service" "ai_tutor" {
  name            = "${var.project}-ai-tutor"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.ai_tutor.arn
  desired_count   = var.desired_count
  launch_type     = "FARGATE"

  network_configuration {
    subnets         = aws_subnet.private[*].id
    security_groups = [aws_security_group.service.id] # backend と同じ 8000 を許可済み
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.ai_tutor.arn
    container_name   = "ai-tutor"
    container_port   = var.backend_container_port
  }

  # CI が新イメージで task definition を更新するため drift を無視
  lifecycle {
    ignore_changes = [task_definition]
  }

  depends_on = [aws_lb_listener.http]
}
