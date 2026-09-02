"""Conversation Service (計画 §1-④ / 仕様書7章)。

役割は「次に何を質問するか決める」。すぐ正解を教えず Teach-back で確認する。
会話ターンの下限/上限はここで担保する (プロンプト任せにしない)。
"""

from app.config import Settings
from app.llm.interface import LLMClient, Message
from app.models import ConversationMessage, Role

SYSTEM_PROMPT = (
    "あなたは生徒の学びに興味津々な、親しみやすいAIチューターです。\n"
    "試験官のように問い詰めるのではなく、「何を勉強したの？」「へえ、もっと教えて！」という\n"
    "好奇心と応援のスタンスで、フレンドリーに話しかけてください。\n"
    "\n"
    "- まずは生徒が今日学んだことに素直に興味を示し、一緒に楽しむ雰囲気を作ってください。\n"
    "- 生徒に自分の言葉で説明してもらい、理解が深まるよう手伝います（Teach-back）。\n"
    "- 説明が曖昧でも否定しません。まず「いいね！」「なるほど！」と受け止めてから、\n"
    "  「その部分をもう少し教えてくれる？」とやわらかく掘り下げてください。\n"
    "- 詰問や矢継ぎ早の追及はしません。一度に一つだけ、軽い質問をします。\n"
    "- 敬語すぎず、親しみやすい口調で。会話は3〜7ターンくらいで和やかに締めてください。"
)

# この回数以上ユーザーが答えたら「終了してよい」と提案できる (ready_to_finish)。
MIN_USER_TURNS_BEFORE_FINISH = 3

STATE_QUESTIONING = "questioning"
STATE_READY_TO_FINISH = "ready_to_finish"

_HARD_CAP_CLOSING = (
    "今日はたくさん話してくれてありがとう！すごくよく伝わってきたよ。"
    "ここで一区切りにしようか。"
)


class ConversationService:
    def __init__(self, llm: LLMClient, settings: Settings) -> None:
        self.llm = llm
        self.settings = settings

    def _model_id(self) -> str | None:
        return self.settings.conversation_model_id or None

    def _to_llm(self, history: list[ConversationMessage]) -> list[Message]:
        return [Message(role=m.role.value, content=m.content) for m in history]

    def opening_message(self) -> str:
        """セッション開始時の最初の質問。"""
        return self.llm.complete(
            system=SYSTEM_PROMPT, messages=[], model_id=self._model_id()
        )

    def next_message(self, history: list[ConversationMessage]) -> tuple[str, str]:
        """次の質問テキストと state を返す。

        - ハード上限 (max_turns) に達したら LLM を呼ばず強制的に締めへ誘導。
        - 下限 (MIN_USER_TURNS_BEFORE_FINISH) を超えたら ready_to_finish を提案。
        """
        user_turns = sum(1 for m in history if m.role == Role.user)
        if user_turns >= self.settings.max_turns:
            return _HARD_CAP_CLOSING, STATE_READY_TO_FINISH

        text = self.llm.complete(
            system=SYSTEM_PROMPT,
            messages=self._to_llm(history),
            model_id=self._model_id(),
        )
        state = (
            STATE_READY_TO_FINISH
            if user_turns >= MIN_USER_TURNS_BEFORE_FINISH
            else STATE_QUESTIONING
        )
        return text, state
