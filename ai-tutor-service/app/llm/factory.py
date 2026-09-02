"""LLM_MODE に応じて LLMClient 実装を選ぶ。"""

from app.config import LLMMode, Settings
from app.llm.interface import LLMClient


def get_llm_client(settings: Settings) -> LLMClient:
    if settings.llm_mode is LLMMode.mock:
        from app.llm.mock import MockLLMClient

        return MockLLMClient()
    if settings.llm_mode is LLMMode.bedrock:
        # Bedrock 実装は後続 PR (計画 §6 step 8) で追加する。
        raise NotImplementedError("bedrock LLM client is not implemented yet")
    raise ValueError(f"unknown LLM_MODE: {settings.llm_mode}")
