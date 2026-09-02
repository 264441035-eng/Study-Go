"""Student Model 更新 (計画 §1-⑤ / 仕様書10章)。

finish 時の Assessment を長期プロフィール (StudentModels) に反映する。
topic 単位で upsert し、confidence は subtopic の平均をとる。
"""

from datetime import datetime, timezone

from app.models import Assessment
from app.repositories.interface import StudentModelRepository


def _avg_confidence(assessment: Assessment) -> float:
    confs = [st.confidence for st in assessment.subtopics]
    return sum(confs) / len(confs) if confs else 0.5


class StudentModelService:
    def __init__(self, repo: StudentModelRepository) -> None:
        self.repo = repo

    def apply(self, user_id: str, subject: str, assessment: Assessment) -> None:
        self.repo.upsert_topic(
            user_id,
            subject,
            assessment.topic,
            score=assessment.overall_score,
            confidence=round(_avg_confidence(assessment), 2),
            weaknesses=list(assessment.weaknesses),
            last_assessed_at=datetime.now(timezone.utc).isoformat(),
        )
