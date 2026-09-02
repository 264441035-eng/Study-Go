"""Conversation Service (計画 §1-④ / 仕様書7章)。

役割は「次に何を質問するか決める」。すぐ正解を教えず Teach-back で確認する。
会話ターンの下限/上限はここで担保する (プロンプト任せにしない)。
"""

from app.config import Settings
from app.llm.interface import LLMClient, Message
from app.models import ConversationMessage, Role, Session
from app.services.concept_map import get_concept, get_concepts

SYSTEM_PROMPT = (
    "あなたは生徒の学びに興味津々な、親しみやすいAIチューターです。\n"
    "試験官のように問い詰めるのではなく、好奇心と応援のスタンスで話してください。\n"
    "\n"
    "【会話の目的】\n"
    "生徒が今日学んだ内容を、自分の言葉で説明できるか確認してください。\n"
    "単に学習内容を聞くだけで終わらず、重要な概念を一つずつ深掘りしてください。\n"
    "\n"
    "【質問のルール】\n"
    "- 生徒が最初に答えた学習内容から、重要な概念を特定してください。\n"
    "- 一度に一つの概念だけを確認してください。\n"
    "- 「定義 → 意味 → 理由 → 具体例」のように段階的に深掘りしてください。\n"
    "- 生徒が正しく説明できた場合は、次の重要概念へ進んでください。\n"
    "- 説明が曖昧な場合は、すぐに正解を教えず、ヒントや別の質問で確認してください。\n"
    "- 生徒の回答を踏まえて、前の質問と重複しない質問をしてください。\n"
    "- 数学の場合は、可能であれば式や具体的な数値を使った質問もしてください。\n"
    "- 最後まで答えを教えるのではなく、生徒自身に説明させてください。\n"
    "\n"
    "【一次関数の例】\n"
    "生徒が一次関数を学んだ場合、y=ax+b、a（傾き）、b（y切片）、"
    "変化の割合、具体的な式、グラフとの関係などを確認してください。\n"
    "\n"
    "【口調】\n"
    "- 説明が曖昧でも否定しません。\n"
    "- 「いいね！」「なるほど！」などで受け止めてください。\n"
    "- 一度に一つだけ、軽い質問をしてください。\n"
    "- 敬語すぎず、親しみやすい口調にしてください。\n"
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
            system=SYSTEM_PROMPT,
            messages=[],
            model_id=self._model_id(),
        )

    def next_message(
        self,
        history: list[ConversationMessage],
        session: Session,
    ) -> tuple[str, str]:
        """現在のconceptを踏まえて次の質問を生成する。"""

        user_turns = sum(1 for m in history if m.role == Role.user)

        if user_turns >= self.settings.max_turns:
            return _HARD_CAP_CLOSING, STATE_READY_TO_FINISH

        concept = None

        if session.topic:
            concept = get_concept(
                session.topic,
                session.concept_index,
            )

        concept_instruction = ""

        if concept:
            concept_instruction = (
                "\n\n"
                "【今回確認する重要概念】\n"
                f"{concept['description']}\n"
                "\n"
                "今回の質問では、この概念だけを確認してください。\n"
                "すでに同じ概念について十分説明できている場合は、"
                "次の概念につながる質問をしてください。\n"
            )

        system_prompt = SYSTEM_PROMPT + concept_instruction

        text = self.llm.complete(
            system=system_prompt,
            messages=self._to_llm(history),
            model_id=self._model_id(),
        )

        state = (
            STATE_READY_TO_FINISH
            if user_turns >= MIN_USER_TURNS_BEFORE_FINISH
            else STATE_QUESTIONING
        )

        return text, state