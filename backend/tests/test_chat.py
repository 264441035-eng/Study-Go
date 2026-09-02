from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_chat_message_and_reply():
    # メッセージを送信
    resp = client.post(
        "/api/chat/message",
        json={"message": "今日は二次関数について勉強した"},
    )

    assert resp.status_code == 200
    assert resp.json()["message"] == "今日は二次関数について勉強した"

    # キャラクターの返答を取得
    resp = client.get("/api/chat/reply")

    assert resp.status_code == 200
    assert "二次関数" in resp.json()["message"]


def test_chat_today_and_question():
    # 今日の学習内容を送信
    resp = client.post(
        "/api/chat/today",
        json={"content": "今日は二次関数について勉強しました"},
    )

    assert resp.status_code == 200
    assert resp.json()["message"] == "今日は二次関数について勉強しました"

    # キャラクターからの復習問題を取得
    resp = client.get("/api/chat/question")

    assert resp.status_code == 200
    assert "二次関数" in resp.json()["message"]
    assert "平方完成" in resp.json()["message"]


def test_chat_explanation_and_feedback():
    # 学習内容について説明
    resp = client.post(
        "/api/chat/explanation",
        json={"explanation": "二次関数の平方完成は頂点を求めるため"},
    )

    assert resp.status_code == 200
    assert resp.json()["message"] == "二次関数の平方完成は頂点を求めるため"

    # キャラクターからフィードバックを取得
    resp = client.get("/api/chat/feedback")

    assert resp.status_code == 200
    assert "頂点" in resp.json()["message"]


def test_chat_explanation_detail():
    # 詳しい説明を送信
    resp = client.post(
        "/api/chat/message",
        json={
            "message": (
                "二次関数の式を変形して、"
                "グラフの頂点の座標や軸を求めるためにする計算だよ。"
            )
        },
    )

    assert resp.status_code == 200
    assert "グラフ" in resp.json()["message"] or "変形" in resp.json()["message"]

    # ボーナスポイント付きの返答を取得
    resp = client.get("/api/chat/reply")

    assert resp.status_code == 200
    assert "大正解" in resp.json()["message"]
    assert "ボーナスポイントGET" in resp.json()["message"]