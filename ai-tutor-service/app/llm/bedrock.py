"""Bedrock LLM (LLM_MODE=bedrock)。

Amazon Bedrock Converse API を使う (モデル差異を吸収する統一API)。
  - complete            … 1回応答 (会話 = Haiku)
  - stream              … トークンストリーミング (音声移行を見据えた作り; 計画 §1付随)
  - complete_structured … Tool Use で構造化出力を強制 (評価 = Sonnet, taxonomy enum)

認証は Default Credential Chain (aws sso login / 環境変数 / IAMロール)。
モデルIDは settings で pin。リージョン availability は要確認 (計画 §1-③)。
"""

from collections.abc import Iterator

import boto3
from botocore.config import Config

from app.config import Settings
from app.llm.interface import LLMClient, Message

# messages が空のとき (opening_message) に注入する開始プロンプト。
# Converse API は messages を空にできないため。
_START_TURN = [{"role": "user", "content": [{"text": "（会話を開始してください）"}]}]

_STRUCTURED_TOOL_NAME = "record_assessment"


class BedrockLLMClient(LLMClient):
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._default_model = settings.conversation_model_id
        self._client = boto3.client(
            "bedrock-runtime",
            region_name=settings.bedrock_region,
            config=Config(retries={"max_attempts": 3, "mode": "adaptive"}),
        )

    def _model(self, model_id: str | None) -> str:
        chosen = model_id or self._default_model
        if not chosen:
            raise RuntimeError(
                "Bedrock model id is not configured "
                "(CONVERSATION_MODEL_ID / ASSESSMENT_MODEL_ID)"
            )
        return chosen

    @staticmethod
    def _converse_messages(messages: list[Message]) -> list[dict]:
        if not messages:
            return list(_START_TURN)
        return [{"role": m.role, "content": [{"text": m.content}]} for m in messages]

    @staticmethod
    def _system(system: str) -> list[dict]:
        return [{"text": system}] if system else []

    def complete(
        self,
        *,
        system: str,
        messages: list[Message],
        model_id: str | None = None,
        max_tokens: int = 1024,
    ) -> str:
        resp = self._client.converse(
            modelId=self._model(model_id),
            system=self._system(system),
            messages=self._converse_messages(messages),
            inferenceConfig={"maxTokens": max_tokens},
        )
        return resp["output"]["message"]["content"][0]["text"]

    def stream(
        self,
        *,
        system: str,
        messages: list[Message],
        model_id: str | None = None,
        max_tokens: int = 1024,
    ) -> Iterator[str]:
        resp = self._client.converse_stream(
            modelId=self._model(model_id),
            system=self._system(system),
            messages=self._converse_messages(messages),
            inferenceConfig={"maxTokens": max_tokens},
        )
        for event in resp["stream"]:
            delta = event.get("contentBlockDelta", {}).get("delta", {})
            if "text" in delta:
                yield delta["text"]

    def complete_structured(
        self,
        *,
        system: str,
        messages: list[Message],
        schema: dict,
        model_id: str | None = None,
        max_tokens: int = 1024,
    ) -> dict:
        tool_config = {
            "tools": [
                {
                    "toolSpec": {
                        "name": _STRUCTURED_TOOL_NAME,
                        "description": "口頭試問の構造化評価を記録する。",
                        "inputSchema": {"json": schema},
                    }
                }
            ],
            # 必ずこのツールを呼ばせる = 構造化出力を強制。
            "toolChoice": {"tool": {"name": _STRUCTURED_TOOL_NAME}},
        }
        resp = self._client.converse(
            modelId=self._model(model_id),
            system=self._system(system),
            messages=self._converse_messages(messages),
            inferenceConfig={"maxTokens": max_tokens},
            toolConfig=tool_config,
        )
        for block in resp["output"]["message"]["content"]:
            if "toolUse" in block:
                return block["toolUse"]["input"]
        raise RuntimeError("Bedrock response contained no toolUse block")
