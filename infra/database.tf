# =====================================================================
# backend 用 RDS PostgreSQL
#
# PR #7 (create database) で backend の起動コマンドが
#   python -c 'from app.database import init_db; init_db()' && uvicorn ...
# となり、起動時に DATABASE_URL へ接続するようになった。AWS 側に DB が
# 無かったため localhost:5432 に繋ぎにいって連続クラッシュしていた。
# ここで RDS を新設し、DATABASE_URL を SSM SecureString 経由で backend に注入する。
#
# マージ安全性のため、この機能で増える variable / output / resource は
# すべてこのファイルに閉じ込め、共有ファイルの編集は ecs.tf（backend の
# container 定義に secrets を 1 つ足すだけ）に限定している。ai-tutor-phase1
# は ecs.tf を変更しないため、後続マージで競合しない。
# =====================================================================

variable "db_name" {
  description = "作成するデータベース名"
  type        = string
  default     = "study_go"
}

variable "db_username" {
  description = "DB マスターユーザー名"
  type        = string
  default     = "study_go"
}

variable "db_password" {
  description = "DB マスターパスワード。TF_VAR_db_password で渡す（state に保存される点に注意）"
  type        = string
  sensitive   = true
}

variable "db_instance_class" {
  description = "RDS インスタンスクラス"
  type        = string
  default     = "db.t4g.micro"
}

variable "db_allocated_storage" {
  description = "RDS ストレージ (GiB)"
  type        = number
  default     = 20
}

variable "db_engine_version" {
  description = "PostgreSQL メジャーバージョン"
  type        = string
  default     = "16"
}

# --- プライベートサブネットに配置 ---
resource "aws_db_subnet_group" "main" {
  name       = "${var.project}-db-subnet"
  subnet_ids = aws_subnet.private[*].id
  tags       = { Name = "${var.project}-db-subnet" }
}

# --- DB は ECS サービス SG からの 5432 のみ許可 ---
resource "aws_security_group" "database" {
  name        = "${var.project}-db-sg"
  description = "RDS ingress from ECS service SG only"
  vpc_id      = aws_vpc.main.id

  ingress {
    description     = "PostgreSQL from ECS tasks"
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.service.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = { Name = "${var.project}-db-sg" }
}

resource "aws_db_instance" "postgres" {
  identifier     = "${var.project}-postgres"
  engine         = "postgres"
  engine_version = var.db_engine_version
  instance_class = var.db_instance_class

  allocated_storage = var.db_allocated_storage
  storage_type      = "gp3"
  storage_encrypted = true

  db_name  = var.db_name
  username = var.db_username
  password = var.db_password
  port     = 5432

  db_subnet_group_name   = aws_db_subnet_group.main.name
  vpc_security_group_ids = [aws_security_group.database.id]
  publicly_accessible    = false
  multi_az               = false

  # トライアル用の割り切り設定
  skip_final_snapshot = true
  deletion_protection = false
  apply_immediately   = true

  tags = { Name = "${var.project}-postgres" }
}

# --- backend が読む DATABASE_URL を SSM SecureString に格納 ---
# app/database.py が期待する SQLAlchemy(psycopg2) 形式で組み立てる。
resource "aws_ssm_parameter" "database_url" {
  name = "/${var.project}/backend/database-url"
  type = "SecureString"
  value = format(
    "postgresql+psycopg2://%s:%s@%s:%s/%s",
    var.db_username,
    var.db_password,
    aws_db_instance.postgres.address,
    aws_db_instance.postgres.port,
    var.db_name,
  )
}

# 実行ロールが SecureString を読めるように（AWS 管理キーなので kms:Decrypt は不要）
data "aws_iam_policy_document" "backend_db_ssm" {
  statement {
    actions   = ["ssm:GetParameters"]
    resources = [aws_ssm_parameter.database_url.arn]
  }
}

resource "aws_iam_role_policy" "backend_db_ssm" {
  name   = "${var.project}-backend-db-ssm"
  role   = aws_iam_role.ecs_task_execution.id
  policy = data.aws_iam_policy_document.backend_db_ssm.json
}

output "database_endpoint" {
  description = "RDS PostgreSQL のエンドポイント"
  value       = aws_db_instance.postgres.address
}
