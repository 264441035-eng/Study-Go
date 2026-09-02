from pydantic import BaseModel, Field


class DailyReport(BaseModel):
    date: str  # YYYY-MM-DD
    subject: str | None = None
    topic: str
    understanding_score: int = Field(ge=0, le=100)
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    comment: str = ""
    xp: int = 0
