"""Bedrock 疎通確認 CLI (計画 §6 step 8-9 の検証)。

Default Credential Chain で実 Bedrock を呼び、3経路 (complete / stream /
complete_structured=ToolUse) が通ることを確認する。実課金が発生する。

    LLM_MODE=bedrock BEDROCK_REGION=ap-northeast-1 \\
      CONVERSATION_MODEL_ID=jp.anthropic.claude-haiku-4-5-20251001-v1:0 \\
      ASSESSMENT_MODEL_ID=global.anthropic.claude-sonnet-5 \\
      python -m scripts.bedrock_smoke
"""

import json

from app.config import get_settings
from app.llm.bedrock import BedrockLLMClient
from app.llm.interface import Message
from app.services.assessment import ASSESSMENT_SYSTEM_PROMPT, build_assessment_schema


def main() -> None:
    s = get_settings()
    client = BedrockLLMClient(s)
    print(
        f"region={s.bedrock_region}\n"
        f"conversation_model={s.conversation_model_id}\n"
        f"assessment_model={s.assessment_model_id}"
    )

    print("\n[1/3] complete (会話モデル) -----------------------------")
    out = client.complete(
        system="あなたは親しみやすい家庭教師です。日本語で簡潔に。",
        messages=[Message("user", "二次関数の平方完成について、生徒に一問だけ質問して。")],
        max_tokens=200,
    )
    print(out)

    print("\n[2/3] stream (トークンストリーミング) --------------------")
    for chunk in client.stream(
        system="日本語で簡潔に。",
        messages=[Message("user", "『準備OK』と5語以内で返して。")],
        max_tokens=50,
    ):
        print(chunk, end="", flush=True)
    print()

    if not s.assessment_model_id:
        print("\n[3/3] structured: ASSESSMENT_MODEL_ID 未設定のためスキップ")
        return

    print("\n[3/3] complete_structured (評価モデル / Tool Use) --------")
    raw = client.complete_structured(
        system=ASSESSMENT_SYSTEM_PROMPT,
        messages=[
            Message("assistant", "二次関数について、自分の言葉で説明してみて。"),
            Message("user", "平方完成をして y=a(x-p)^2+q の形にすると頂点が (p, q) と分かります。"),
        ],
        schema=build_assessment_schema("math"),
        model_id=s.assessment_model_id,
        max_tokens=1024,
    )
    print(json.dumps(raw, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
