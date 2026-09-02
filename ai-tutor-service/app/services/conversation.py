"""Conversation Service (計画 §1-④ / 仕様書7章)。

役割は「次に何を質問するか決める」。すぐ正解を教えず Teach-back で確認する。
会話ターンの下限/上限はここで担保する (プロンプト任せにしない)。
"""

from app.config import Settings
from app.llm.interface import LLMClient, Message
from app.models import ConversationMessage, Role

SYSTEM_PROMPT = (
    "あなたは受験生の理解度を確認するAI Tutorです。\n"
    "あなたの目的は問題を解くことではなく、受験生が本当に理解しているかを確認することです。\n"
    "Teach-back形式で質問してください。\n"
    "ユーザーが曖昧な説明をした場合、すぐに答えを教えず追加質問してください。\n"
    "一度に一つだけ質問してください。会話は3〜7ターン程度で締めてください。"
)

# この回数以上ユーザーが答えたら「終了してよい」と提案できる (ready_to_finish)。
MIN_USER_TURNS_BEFORE_FINISH = 3

STATE_QUESTIONING = "questioning"
STATE_READY_TO_FINISH = "ready_to_finish"

_HARD_CAP_CLOSING = "ここまでの説明で十分確認できました。学習を終了しましょう。"


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
