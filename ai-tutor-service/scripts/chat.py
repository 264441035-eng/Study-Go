"""ローカル対話 CLI — 実際の口頭試問を試す (サーバー不要, in-process)。

  LLM_MODE=bedrock python -m scripts.chat   # 実 Bedrock で会話
  LLM_MODE=mock    python -m scripts.chat   # 定型モックで会話 (課金なし)

コマンド:
  /finish  … 会話を終了して評価 (Assessment + Daily Report) を表示
  /quit    … 評価せず終了
"""

from app.config import get_settings
from app.llm import get_llm_client
from app.models import ConversationMessage, Role, Session
from app.services.assessment import AssessmentService
from app.services.conversation import STATE_READY_TO_FINISH, ConversationService
from app.services.report import ReportService


def main() -> None:
    settings = get_settings()
    llm = get_llm_client(settings)
    conv = ConversationService(llm, settings)
    assessor = AssessmentService(llm, settings)
    reporter = ReportService()

    session = Session(user_id="local-user", subject="math")
    history: list[ConversationMessage] = []

    def record(role: Role, content: str) -> None:
        history.append(
            ConversationMessage(session_id=session.session_id, role=role, content=content)
        )

    print(
        f"[mode] LLM={settings.llm_mode.value}  "
        f"conversation={settings.conversation_model_id or '-'}"
    )
    print("会話を開始します。'/finish' で評価、'/quit' で終了。")

    opening = conv.opening_message()
    record(Role.assistant, opening)
    print(f"\nAI> {opening}")

    finished_normally = False
    while True:
        try:
            user = input("\nあなた> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not user:
            continue
        if user in ("/quit", "/exit"):
            print("(評価せず終了しました)")
            return
        if user == "/finish":
            finished_normally = True
            break

        record(Role.user, user)
        text, state = conv.next_message(history)
        record(Role.assistant, text)
        print(f"\nAI> {text}")
        print(f"    [state={state}]")
        if state == STATE_READY_TO_FINISH:
            print("    (十分確認できました。'/finish' で評価に進めます)")

    if not finished_normally and not any(m.role is Role.user for m in history):
        return

    print("\n=== 評価中 (Assessment: Sonnet) ===")
    assessment = assessor.assess(session, history)
    report = reporter.build(session, assessment)
    print(f"topic      : {assessment.topic}")
    print(f"score      : {assessment.overall_score}")
    print(f"strengths  : {assessment.strengths}")
    print(f"weaknesses : {assessment.weaknesses}")
    print(f"XP         : {report.xp}")
    print(f"comment    : {report.comment}")


if __name__ == "__main__":
    main()
