"""DynamoDB テーブル作成 CLI (local 用)。

DynamoDB Local を起動した上で:
    DATABASE_MODE=local DYNAMODB_ENDPOINT_URL=http://localhost:8000 \\
        python -m scripts.create_tables
"""

from app.config import get_settings
from app.repositories.dynamodb import ensure_tables


def main() -> None:
    settings = get_settings()
    ensure_tables(settings)
    print(
        f"tables ready: {settings.sessions_table}, {settings.student_models_table} "
        f"(endpoint={settings.dynamodb_endpoint_url or 'AWS'})"
    )


if __name__ == "__main__":
    main()
