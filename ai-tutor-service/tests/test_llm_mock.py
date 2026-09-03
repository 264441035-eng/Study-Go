
from app.config import LLMMode, Settings
from app.llm import Message, get_llm_client
from app.llm.mock import MockLLMClient
from app.services import persona as persona_tone


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


def test_persona_changes_question_tone():
    # system プロンプトに口調（persona）マーカーが載っていると、
    # mock でも会話の台本が切り替わる（Bedrock 未接続でも口調を確認できる）。
    c = _client()
    neutral = c.complete(system="", messages=[])
    tsundere = c.complete(
        system=persona_tone.conversation_tone(persona_tone.PERSONA_TSUNDERE),
        messages=[],
    )
    onee = c.complete(
        system=persona_tone.conversation_tone(persona_tone.PERSONA_ONEE),
        messages=[],
    )
    assert neutral != tsundere != onee != neutral
    assert "なさいよ" in tsundere  # ツンデレらしい語尾
    assert "かしら" in onee  # お姉さんらしい語尾


def test_structured_stays_factual_regardless_of_persona():
    # 評価項目そのもの（strengths/weaknesses）は口調で変えない。
    # 口調付けは report 層が行うため、ここで飾ると二重装飾になる。
    c = _client()
    base = c.complete_structured(system="", messages=[], schema={})
    with_persona = c.complete_structured(
        system=persona_tone.assessment_tone(persona_tone.PERSONA_TSUNDERE),
        messages=[],
        schema={},
    )
    assert base["strengths"] == with_persona["strengths"]
    assert base["weaknesses"] == with_persona["weaknesses"]
