from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_chat_today_and_question() -> None:
    # 今日勉強した内容を送信
    resp = client.post(
        "/api/chat/today",
        json={
            "content": "今日はAWSのIAMについて勉強しました"
        },
    )

    assert resp.status_code == 200
    assert resp.json()["message"] == "今日はAWSのIAMについて勉強しました"

    # AIからの質問を取得
    resp = client.get("/api/chat/question")

    assert resp.status_code == 200
    assert "IAM" in resp.json()["message"]


def test_chat_explanation_and_feedback() -> None:
    # 学習内容を説明
    resp = client.post(
        "/api/chat/explanation",
        json={
            "explanation": (
                "IAMはAWSのユーザーやサービスが利用できる"
                "リソースへのアクセス権限を管理するサービスです。"
            )
        },
    )

    assert resp.status_code == 200
    assert "IAM" in resp.json()["message"]

    # AIからのフィードバックを取得
    resp = client.get("/api/chat/feedback")

    assert resp.status_code == 200
    assert len(resp.json()["message"]) > 0


def test_chat_message_and_reply() -> None:
    # キャラクターにメッセージを送信
    resp = client.post(
        "/api/chat/message",
        json={
            "message": "今日はIAMについて勉強した"
        },
    )

    assert resp.status_code == 200
    assert resp.json()["message"] == "今日はIAMについて勉強した"

    # キャラクターからの返信を取得
    resp = client.get("/api/chat/reply")

    assert resp.status_code == 200
    assert "IAM" in resp.json()["message"]