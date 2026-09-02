resource "aws_ecs_cluster" "main" {
  name = "${var.project}-cluster"

  setting {
    name  = "containerInsights"
    value = "enabled"
  }
}

resource "aws_cloudwatch_log_group" "backend" {
  name              = "/ecs/${var.project}-backend"
  retention_in_days = 14
}

resource "aws_cloudwatch_log_group" "frontend" {
  name              = "/ecs/${var.project}-frontend"
  retention_in_days = 14
}

# ---------------- Backend ----------------
resource "aws_ecs_task_definition" "backend" {
  family                   = "${var.project}-backend"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = var.backend_cpu
  memory                   = var.backend_memory
  execution_role_arn       = aws_iam_role.ecs_task_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  container_definitions = jsonencode([
    {
      name      = "backend"
      image     = "${aws_ecr_repository.backend.repository_url}:${var.image_tag}"
      essential = true
      portMappings = [
        { containerPort = var.backend_container_port, protocol = "tcp" }
      ]
      environment = [
        # 同一 ALB オリジンで配信するため CORS は基本不要だが、明示しておく
        { name = "CORS_ORIGINS", value = "http://${aws_lb.main.dns_name}" },
        # /api/chat/* プロキシ(chat.py)の転送先。ALB の /sessions* ルールが ai-tutor に振り分ける。
        # 未設定だと localhost:8000（=自分自身）へ転送し 404 になる。
        { name = "AI_TUTOR_SERVICE_URL", value = "http://${aws_lb.main.dns_name}" }
      ]
      # 起動時 init_db() が接続する DB 接続文字列を SSM SecureString から注入（database.tf）。
      # AI Tutor ログイン用に JWT 署名鍵(ai-tutor と共有)と認証情報も SSM から注入する。
      secrets = [
        { name = "DATABASE_URL", valueFrom = aws_ssm_parameter.database_url.arn },
        { name = "JWT_SECRET", valueFrom = aws_ssm_parameter.jwt_secret.arn },
        { name = "AUTH_USERS", valueFrom = aws_ssm_parameter.auth_users.arn },
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.backend.name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "backend"
        }
      }
    }
  ])
}

resource "aws_ecs_service" "backend" {
  name            = "${var.project}-backend"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.backend.arn
  desired_count   = var.desired_count
  launch_type     = "FARGATE"

  network_configuration {
    subnets         = aws_subnet.private[*].id
    security_groups = [aws_security_group.service.id]
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.backend.arn
    container_name   = "backend"
    container_port   = var.backend_container_port
  }

  # CI が新イメージで task definition を更新するため、tag 差分での常時 drift を無視
  lifecycle {
    ignore_changes = [task_definition]
  }

  depends_on = [aws_lb_listener.http]
}

# ---------------- Backend ログイン認証 (AI Tutor 用) ----------------
# 事前に決めた ID/PW を bcrypt ハッシュ化した JSON を SSM SecureString に格納し、
# backend に AUTH_USERS として注入する。値は TF_VAR_auth_users_json で渡す
#   （平文パスワードは含まず bcrypt ハッシュのみ。生成は backend/scripts/hash_password.py）。
# 署名鍵 JWT_SECRET は ai-tutor と同じ SSM パラメータ (ai_tutor.tf) を共有する。
resource "aws_ssm_parameter" "auth_users" {
  name  = "/${var.project}/backend/auth-users"
  type  = "SecureString"
  value = var.auth_users_json
}

variable "auth_users_json" {
  description = "AI Tutor ログインの認証情報 JSON (user_id -> bcrypt ハッシュ)。TF_VAR_auth_users_json で渡す。state に保存される点に注意"
  type        = string
  sensitive   = true
}

# backend の実行ロールが JWT_SECRET / AUTH_USERS を読めるようにする
# （AWS 管理キーの SecureString なので kms:Decrypt は不要）。
data "aws_iam_policy_document" "backend_auth_ssm" {
  statement {
    actions = ["ssm:GetParameters"]
    resources = [
      aws_ssm_parameter.jwt_secret.arn,
      aws_ssm_parameter.auth_users.arn,
    ]
  }
}

resource "aws_iam_role_policy" "backend_auth_ssm" {
  name   = "${var.project}-backend-auth-ssm"
  role   = aws_iam_role.ecs_task_execution.id
  policy = data.aws_iam_policy_document.backend_auth_ssm.json
}

# ---------------- Frontend ----------------
resource "aws_ecs_task_definition" "frontend" {
  family                   = "${var.project}-frontend"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = var.frontend_cpu
  memory                   = var.frontend_memory
  execution_role_arn       = aws_iam_role.ecs_task_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  container_definitions = jsonencode([
    {
      name      = "frontend"
      image     = "${aws_ecr_repository.frontend.repository_url}:${var.image_tag}"
      essential = true
      portMappings = [
        { containerPort = var.frontend_container_port, protocol = "tcp" }
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.frontend.name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "frontend"
        }
      }
    }
  ])
}

resource "aws_ecs_service" "frontend" {
  name            = "${var.project}-frontend"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.frontend.arn
  desired_count   = var.desired_count
  launch_type     = "FARGATE"

  network_configuration {
    subnets         = aws_subnet.private[*].id
    security_groups = [aws_security_group.service.id]
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.frontend.arn
    container_name   = "frontend"
    container_port   = var.frontend_container_port
  }

  lifecycle {
    ignore_changes = [task_definition]
  }

  depends_on = [aws_lb_listener.http]
}
