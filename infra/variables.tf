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

variable "github_repo" {
  description = "OIDC を許可する GitHub リポジトリ (owner/repo)"
  type        = string
  default     = "264441035-eng/Study-Go"
}
