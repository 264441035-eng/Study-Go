variable "aws_region" {
  description = "デプロイ先リージョン"
  type        = string
  default     = "ap-northeast-1"
}

variable "project" {
  description = "リソース名のプレフィックス"
  type        = string
  default     = "study-go"
}

variable "vpc_cidr" {
  description = "VPC の CIDR"
  type        = string
  default     = "10.0.0.0/16"
}

variable "az_count" {
  description = "利用する AZ 数（パブリック/プライベート各 AZ に 1 サブネット）"
  type        = number
  default     = 2
}

variable "backend_container_port" {
  description = "FastAPI コンテナのポート"
  type        = number
  default     = 8000
}

variable "frontend_container_port" {
  description = "nginx コンテナのポート"
  type        = number
  default     = 80
}

variable "image_tag" {
  description = "ECS が参照するイメージタグ。CI では commit SHA を渡す"
  type        = string
  default     = "latest"
}

variable "desired_count" {
  description = "各サービスの希望タスク数"
  type        = number
  default     = 1
}

variable "backend_cpu" {
  type    = number
  default = 256
}

variable "backend_memory" {
  type    = number
  default = 512
}

variable "frontend_cpu" {
  type    = number
  default = 256
}

variable "frontend_memory" {
  type    = number
  default = 512
}

variable "ai_tutor_cpu" {
  type    = number
  default = 256
}

variable "ai_tutor_memory" {
  type    = number
  default = 512
}

variable "ai_tutor_app_env" {
  description = "AI Tutor の APP_ENV。local 以外にすると /dev/token が無効化される"
  type        = string
  default     = "production"
}

variable "ai_tutor_conversation_model_id" {
  description = "会話用モデル (Bedrock jp.* Inference Profile)"
  type        = string
  default     = "jp.anthropic.claude-haiku-4-5-20251001-v1:0"
}

variable "ai_tutor_assessment_model_id" {
  description = "評価用モデル (Bedrock jp.* Inference Profile)"
  type        = string
  default     = "jp.anthropic.claude-sonnet-4-5-20250929-v1:0"
}

variable "ai_tutor_sessions_table" {
  type    = string
  default = "ai-tutor-sessions"
}

variable "ai_tutor_student_models_table" {
  type    = string
  default = "ai-tutor-student-models"
}

variable "github_repo" {
  description = "OIDC を許可する GitHub リポジトリ (owner/repo)"
  type        = string
  default     = "264441035-eng/Study-Go"
}

variable "github_sub_claims" {
  description = <<-EOT
    OIDC の sub クレームに対する許可パターン（StringLike）。
    この組織は sub に不変の数値ID (owner_id / repo_id) を埋め込む設定のため、
    通常形式と ID 付き形式の両方を列挙する。
  EOT
  type        = list(string)
  default = [
    "repo:264441035-eng/Study-Go:*",
    "repo:264441035-eng@292752477/Study-Go@1353213705:*",
  ]
}
