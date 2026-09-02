"""Mock LLM (LLM_MODE=mock)。

外部依存なしで会話フロー/評価を開発・テストするための決定的な応答。
Bedrock 未接続でも Core User Flow を通せる (計画 §16 Mock Mode)。
"""

from collections.abc import Iterator

from app.llm.interface import LLMClient, Message

# Teach-back 形式の質問スクリプト (ユーザー発話回数で進行)。
_QUESTIONS = [
    "今日は何を勉強しましたか？",
    "なるほど。その中心になる考え方を、自分の言葉で説明してみてください。",
    "いいですね。では、なぜそうなるのか理由を説明できますか？",
    "その根拠を、具体例を挙げて説明できますか？",
    "よく理解できていそうです。ここまでの内容を一言でまとめると？",
]

# 決定的なダミー評価 (Assessment schema と概ね一致; 正規化は Assessment 側で行う)。
_MOCK_ASSESSMENT = {
    "topic": "quadratic_functions",
    "subtopics": [
        {"name": "completing_the_square", "score": 72, "confidence": 0.84},
    ],
    "overall_score": 72,
    "strengths": ["平方完成の計算手順を説明できる"],
    "weaknesses": ["平方完成と頂点形式の関係の説明が曖昧"],
    "recommended_next_action": "review_vertex_form",
}


class MockLLMClient(LLMClient):
    def _next_question(self, messages: list[Message]) -> str:
        user_turns = sum(1 for m in messages if m.role == "user")
        return _QUESTIONS[min(user_turns, len(_QUESTIONS) - 1)]

    def complete(
        self,
        *,
        system: str,
        messages: list[Message],
        model_id: str | None = None,
        max_tokens: int = 1024,
    ) -> str:
        return self._next_question(messages)

    def stream(
        self,
        *,
        system: str,
        messages: list[Message],
        model_id: str | None = None,
        max_tokens: int = 1024,
    ) -> Iterator[str]:
        text = self._next_question(messages)
        # 実 LLM のストリーミングを模して分割して返す。
        for ch in text:
            yield ch

    def complete_structured(
        self,
        *,
        system: str,
        messages: list[Message],
        schema: dict,
        model_id: str | None = None,
        max_tokens: int = 1024,
    ) -> dict:
        return dict(_MOCK_ASSESSMENT)
