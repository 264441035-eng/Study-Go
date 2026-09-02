"""Daily Learning Report 生成 (計画 §1-④ / 仕様書9章)。

Assessment から派生する表示用サマリ。XP は簡易ロジック (MVP)。
"""

from datetime import datetime, timezone

from app.models import Assessment, DailyReport, Session


def compute_xp(overall_score: int) -> int:
    """理解度に比例した簡易 XP。MVP のため単純な係数で算出する。"""
    return round(overall_score * 0.8)


def _humanize_next_action(action: str | None) -> str:
    if not action:
        return ""
    mapping = {
        "review_vertex_form": "平方完成と頂点形式の関係を整理すると、もっとスッキリするはず！",
        "review": "関連するところを、もう一回さらっと見直してみよう。",
    }
    return mapping.get(action, action)


def _build_comment(assessment: Assessment) -> str:
    parts: list[str] = []
    if assessment.strengths:
        parts.append("いいね！ " + "・".join(assessment.strengths) + " はしっかり理解できてるよ。")
    if assessment.weaknesses:
        weak = "・".join(assessment.weaknesses)
        parts.append(f"あとは {weak} をちょっと見直すと、もっとバッチリ！")
    next_action = _humanize_next_action(assessment.recommended_next_action)
    if next_action:
        parts.append(next_action)
    return " ".join(parts) or "今日もよくがんばったね、お疲れさま！"


class ReportService:
    def build(self, session: Session, assessment: Assessment) -> DailyReport:
        return DailyReport(
            date=datetime.now(timezone.utc).date().isoformat(),
            subject=session.subject,
            topic=assessment.topic,
            understanding_score=assessment.overall_score,
            strengths=list(assessment.strengths),
            weaknesses=list(assessment.weaknesses),
            comment=_build_comment(assessment),
            xp=compute_xp(assessment.overall_score),
        )
