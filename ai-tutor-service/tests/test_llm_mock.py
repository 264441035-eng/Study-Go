
from app.config import LLMMode, Settings
from app.llm import Message, get_llm_client
from app.llm.mock import MockLLMClient


def _client() -> MockLLMClient:
    return MockLLMClient()


def test_factory_returns_mock_for_mock_mode():
    client = get_llm_client(Settings(llm_mode=LLMMode.mock))
    assert isinstance(client, MockLLMClient)


def test_factory_returns_bedrock_for_bedrock_mode():
    # 実 API は呼ばない。ファクトリが Bedrock 実装を返すことだけ確認する。
    from app.llm.bedrock import BedrockLLMClient

    client = get_llm_client(
        Settings(llm_mode=LLMMode.bedrock, conversation_model_id="dummy-model")
    )
    assert isinstance(client, BedrockLLMClient)


def test_first_question_when_no_user_turns():
    out = _client().complete(system="", messages=[])
    assert "何を勉強" in out


def test_question_advances_with_user_turns():
    c = _client()
    q0 = c.complete(system="", messages=[])
    q1 = c.complete(system="", messages=[Message("user", "二次関数")])
    assert q0 != q1


def test_stream_concatenates_to_complete():
    c = _client()
    msgs = [Message("user", "二次関数")]
    streamed = "".join(c.stream(system="", messages=msgs))
    assert streamed == c.complete(system="", messages=msgs)


def test_structured_returns_assessment_shape():
    out = _client().complete_structured(system="", messages=[], schema={})
    assert out["topic"] == "quadratic_functions"
    assert 0 <= out["overall_score"] <= 100
    assert out["strengths"] and out["weaknesses"]
