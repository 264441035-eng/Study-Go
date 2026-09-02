output "alb_dns_name" {
  description = "アプリの公開 URL（http://<この値>）"
  value       = aws_lb.main.dns_name
}

output "ecr_backend_repository_url" {
  value = aws_ecr_repository.backend.repository_url
}

output "ecr_frontend_repository_url" {
  value = aws_ecr_repository.frontend.repository_url
}

output "ecs_cluster_name" {
  value = aws_ecs_cluster.main.name
}

output "ecs_backend_service_name" {
  value = aws_ecs_service.backend.name
}

output "ecs_frontend_service_name" {
  value = aws_ecs_service.frontend.name
}

output "ecr_ai_tutor_repository_url" {
  value = aws_ecr_repository.ai_tutor.repository_url
}

output "ecs_ai_tutor_service_name" {
  value = aws_ecs_service.ai_tutor.name
}

output "ai_tutor_chat_url" {
  description = "学生に配布するチャットのベース URL (末尾に ?token=… を付けた個人 URL を配る)"
  value       = "http://${aws_lb.main.dns_name}/#/chat"
}

output "ai_tutor_jwt_secret" {
  description = "学生トークン発行用の署名鍵。`terraform output -raw ai_tutor_jwt_secret` で取得"
  value       = random_password.jwt_secret.result
  sensitive   = true
}

output "github_actions_role_arn" {
  description = "GitHub Actions の aws-actions/configure-aws-credentials に渡す role-to-assume"
  value       = aws_iam_role.github_actions.arn
}
