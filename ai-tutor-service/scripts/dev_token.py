"""開発用トークン発行 CLI。

backend の /login 未実装でもローカルで API を叩けるようにするための補助。
例:
    python -m scripts.dev_token user123
    curl -H "Authorization: Bearer $(python -m scripts.dev_token user123)" ...
"""

import sys

from app.auth import create_access_token
from app.config import get_settings


def main() -> None:
    if len(sys.argv) < 2:
        print("usage: python -m scripts.dev_token <user_id>", file=sys.stderr)
        raise SystemExit(1)
    print(create_access_token(sys.argv[1], get_settings()))


if __name__ == "__main__":
    main()
