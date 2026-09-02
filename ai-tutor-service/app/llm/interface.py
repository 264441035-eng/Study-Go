"""LLM 抽象インターフェース。

音声(将来の realtime)への移行を楽にするため、ストリーミング対応で
テキスト入出力に固定する (計画 §1-音声)。実装は mock / bedrock を切替。
"""

from abc import ABC, abstractmethod
from collections.abc import Iterator
from dataclasses import dataclass


@dataclass
class Message:
    role: str  # "user" | "assistant"
    content: str


class LLMClient(ABC):
    @abstractmethod
    def complete(
        self,
        *,
        system: str,
        messages: list[Message],
        model_id: str | None = None,
        max_tokens: int = 1024,
    ) -> str:
        """会話履歴から次の応答テキストを返す。"""

    @abstractmethod
    def stream(
        self,
        *,
        system: str,
        messages: list[Message],
        model_id: str | None = None,
        max_tokens: int = 1024,
    ) -> Iterator[str]:
        """応答テキストをトークン片で逐次返す (realtime 音声・体感向上用)。"""

    @abstractmethod
    def complete_structured(
        self,
        *,
        system: str,
        messages: list[Message],
        schema: dict,
        model_id: str | None = None,
        max_tokens: int = 1024,
    ) -> dict:
        """schema に沿った構造化出力を返す (Assessment 用)。"""
