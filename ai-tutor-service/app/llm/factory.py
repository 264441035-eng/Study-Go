"""LLM_MODE に応じて LLMClient 実装を選ぶ。"""

from app.config import LLMMode, Settings
from app.llm.interface import LLMClient


def get_llm_client(settings: Settings) -> LLMClient:
    if settings.llm_mode is LLMMode.mock:
        from app.llm.mock import MockLLMClient

        return MockLLMClient()
    if settings.llm_mode is LLMMode.bedrock:
        from app.llm.bedrock import BedrockLLMClient

        return BedrockLLMClient(settings)
    raise ValueError(f"unknown LLM_MODE: {settings.llm_mode}")
