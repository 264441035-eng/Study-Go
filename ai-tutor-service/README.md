# AI Tutor Service

学習内容を口頭試問形式で確認し、理解度を評価して Daily Report を生成する独立 HTTP サービス。
既存 Backend とは HTTP API 経由のみで疎結合に連携する。

- Language: Python 3.12+ / FastAPI
- LLM: Amazon Bedrock (会話 = Claude Haiku 4.5 / 評価 = Claude Sonnet 4.5、`jp.*` Inference Profile)
- 永続化: DynamoDB (Sessions / StudentModels)

> Phase1 の設計判断と実装計画はローカルの `docs/PHASE1_IMPLEMENTATION_PLAN.md` 参照
> (このファイルはリモートに push しない運用)。

## セットアップ

```bash
cd ai-tutor-service
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env
```

## 起動

```bash
uvicorn app.main:app --reload --port 8000
# 動作確認
curl localhost:8000/health
```

## テスト

```bash
pytest
```

## 依存モード

環境変数で依存を差し替えられる（開発効率のため mock を用意）。

| 変数 | 値 | 用途 |
|---|---|---|
| `LLM_MODE` | `mock` \| `bedrock` | LLM をモック応答 / 実 Bedrock |
| `BACKEND_MODE` | `mock` \| `real` | 既存 Backend をモック / 実 API |
| `DATABASE_MODE` | `memory` \| `local` \| `aws` | in-memory / DynamoDB Local / 実 DynamoDB |
| `RAG_MODE` | `mock` \| `bedrock` | Phase1 は `mock` 固定 |

デフォルト（`.env` なし）は全て mock/memory で、外部依存なしに起動できる。

## 実サービス疎通 (任意)

```bash
# Bedrock 疎通 (要 AWS 認証情報; 実課金あり)。complete / stream / Tool Use を検証。
LLM_MODE=bedrock python -m scripts.bedrock_smoke

# DynamoDB Local のテーブル作成 (DynamoDB Local を起動した上で)
DATABASE_MODE=local DYNAMODB_ENDPOINT_URL=http://localhost:8000 \
  python -m scripts.create_tables
```

- Bedrock は ap-northeast-1 で疎通確認済み。組織 SCP が `global.*` / Sonnet 5 を
  deny するため `jp.*` Inference Profile を pin している（`.env.example` 参照）。
- DynamoDB リポジトリは moto によるテスト (`tests/test_dynamodb_repository.py`) で
  memory 実装と同一契約を満たすことを検証済み。
