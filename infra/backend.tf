# tfstate の保存先。
# 初期状態ではローカル state（このブロックはコメントアウト）で動作する。
#
# チーム開発や CI から apply する場合は S3 + DynamoDB のリモート state に切り替える。
# 事前に S3 バケットと DynamoDB テーブルを作成してから、以下のコメントを外して
#   terraform init -reconfigure
# を実行する。
#
# terraform {
#   backend "s3" {
#     bucket         = "study-go-tfstate-<ACCOUNT_ID>"
#     key            = "ecs/terraform.tfstate"
#     region         = "ap-northeast-1"
#     dynamodb_table = "study-go-tflock"
#     encrypt        = true
#   }
# }
