"""Mock LLM (LLM_MODE=mock)。

外部依存なしで会話フロー/評価を開発・テストするための決定的な応答。
Bedrock 未接続でも Core User Flow を通せる (計画 §16 Mock Mode)。

Bedrock は system プロンプトに従って口調（ツンデレ/お姉さん）を変えるが、
mock は本来 system を無視するため、そのままだと口調がまったく反映されない。
デモ/ローカルでも口調の切り替えを確認できるよう、system 中のマーカー
（persona.MARKER_*）から persona を判別し、口調に合わせた台本を返す。
"""

from collections.abc import Iterator

from app.llm.interface import LLMClient, Message
from app.services import persona as persona_tone

# Teach-back 形式の質問スクリプト (ユーザー発話回数で進行)。
# persona 未指定（進化段階に紐づかない/既定）のときの、素直な口調。
_QUESTIONS = [
    "今日は何を勉強しましたか？",
    "なるほど。その中心になる考え方を、自分の言葉で説明してみてください。",
    "いいですね。では、なぜそうなるのか理由を説明できますか？",
    "その根拠を、具体例を挙げて説明できますか？",
    "よく理解できていそうです。ここまでの内容を一言でまとめると？",
]

# ツンデレ（進化前）の台本。中身（段階的な深掘り）は素の版と揃える。
_QUESTIONS_TSUNDERE = [
    "今日は何を勉強したの？ ちゃんと話してみなさいよ。",
    "ふーん。じゃあ、その一番大事なところ、自分の言葉で説明できる？ "
    "べ、別に試してるわけじゃないんだからね。",
    "まあいいわ。で、なんでそうなるのか理由も言ってみなさいよ。",
    "……悪くないじゃない。その根拠、具体例を挙げて説明できる？",
    "ふん、よく頑張ったわね。ここまでを一言でまとめると、どうなるの？",
]

# お姉さん（進化後）の台本。落ち着いて少し上から目線で導く。
_QUESTIONS_ONEE = [
    "今日はどんなことを勉強したのかしら？ 聞かせてちょうだい。",
    "あら、いいわね。その中心になる考え方を、あなたの言葉で説明してみて？",
    "ふふ、上手ね。では、なぜそうなるのか理由も説明できるかしら？",
    "その調子。根拠を具体例で示せると、もっと素敵よ。",
    "よく理解できているわ。ここまでを一言でまとめると、どうなるかしら？",
]

_QUESTIONS_BY_PERSONA = {
    persona_tone.PERSONA_TSUNDERE: _QUESTIONS_TSUNDERE,
    persona_tone.PERSONA_ONEE: _QUESTIONS_ONEE,
}

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

def _detect_persona(system: str) -> str | None:
    """system プロンプト中のマーカーから persona を判別する。"""
    if persona_tone.MARKER_TSUNDERE in system:
        return persona_tone.PERSONA_TSUNDERE
    if persona_tone.MARKER_ONEE in system:
        return persona_tone.PERSONA_ONEE
    return None


class MockLLMClient(LLMClient):
    def _next_question(self, system: str, messages: list[Message]) -> str:
        persona = _detect_persona(system)
        questions = _QUESTIONS_BY_PERSONA.get(persona, _QUESTIONS)
        user_turns = sum(1 for m in messages if m.role == "user")
        return questions[min(user_turns, len(questions) - 1)]

    def complete(
        self,
        *,
        system: str,
        messages: list[Message],
        model_id: str | None = None,
        max_tokens: int = 1024,
    ) -> str:
        return self._next_question(system, messages)

    def stream(
        self,
        *,
        system: str,
        messages: list[Message],
        model_id: str | None = None,
        max_tokens: int = 1024,
    ) -> Iterator[str]:
        text = self._next_question(system, messages)
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
        # strengths/weaknesses は素の事実項目のまま返す。口調付けは report 層
        # （persona.REPORT_PHRASES）が行うので、ここで飾ると二重になる。
        return dict(_MOCK_ASSESSMENT)
