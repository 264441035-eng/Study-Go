"""Assessment Service (計画 §1-④ / 仕様書8章)。

Conversation とは分離し、finish 時に会話履歴全体を構造化評価する。
topic/subtopic は taxonomy の enum で制約・正規化し Student Model を安定させる。
"""

from app import taxonomy
from app.config import Settings
from app.llm.interface import LLMClient, Message
from app.models import Assessment, ConversationMessage, Session, SubtopicScore

ASSESSMENT_SYSTEM_PROMPT = (
    "あなたは学習評価の専門家です。以下の口頭試問の会話から、受験生の理解度を"
    "客観的に採点し、構造化して出力してください。会話用の応答をそのまま流用せず、"
    "説明の正確性・理解の深さを評価します。"
)

DEFAULT_SUBJECT = "math"


def build_assessment_schema(subject: str) -> dict:
    """Structured Output 用スキーマ。topic は該当教科の enum に制約する。"""
    return {
        "type": "object",
        "properties": {
            "topic": {"type": "string", "enum": taxonomy.allowed_topics(subject)},
            "subtopics": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "score": {"type": "integer", "minimum": 0, "maximum": 100},
                        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                    },
                    "required": ["name", "score", "confidence"],
                },
            },
            "overall_score": {"type": "integer", "minimum": 0, "maximum": 100},
            "strengths": {"type": "array", "items": {"type": "string"}},
            "weaknesses": {"type": "array", "items": {"type": "string"}},
            "recommended_next_action": {"type": "string"},
        },
        "required": ["topic", "overall_score", "strengths", "weaknesses"],
    }


def _clamp_int(value: object, lo: int, hi: int) -> int:
    try:
        return max(lo, min(hi, int(value)))  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return lo


def _clamp_float(value: object, lo: float, hi: float) -> float:
    try:
        return max(lo, min(hi, float(value)))  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return lo


class AssessmentService:
    def __init__(self, llm: LLMClient, settings: Settings) -> None:
        self.llm = llm
        self.settings = settings

    def assess(
        self, session: Session, history: list[ConversationMessage]
    ) -> Assessment:
        subject = session.subject or DEFAULT_SUBJECT
        raw = self.llm.complete_structured(
            system=ASSESSMENT_SYSTEM_PROMPT,
            messages=[Message(role=m.role.value, content=m.content) for m in history],
            schema=build_assessment_schema(subject),
            model_id=self.settings.assessment_model_id or None,
        )

        topic = taxonomy.normalize_topic(subject, raw.get("topic", taxonomy.OTHER))
        subtopics = [
            SubtopicScore(
                name=taxonomy.normalize_subtopic(
                    subject, topic, st.get("name", taxonomy.OTHER)
                ),
                score=_clamp_int(st.get("score", 0), 0, 100),
                confidence=_clamp_float(st.get("confidence", 0.0), 0.0, 1.0),
            )
            for st in raw.get("subtopics", [])
        ]
        return Assessment(
            session_id=session.session_id,
            topic=topic,
            subtopics=subtopics,
            overall_score=_clamp_int(raw.get("overall_score", 0), 0, 100),
            strengths=list(raw.get("strengths", [])),
            weaknesses=list(raw.get("weaknesses", [])),
            recommended_next_action=raw.get("recommended_next_action"),
        )
