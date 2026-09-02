from pydantic import BaseModel, Field


class SubtopicScore(BaseModel):
    name: str
    score: int = Field(ge=0, le=100)
    confidence: float = Field(ge=0.0, le=1.0)


class Assessment(BaseModel):
    session_id: str
    topic: str
    subtopics: list[SubtopicScore] = Field(default_factory=list)
    overall_score: int = Field(ge=0, le=100)
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    recommended_next_action: str | None = None
