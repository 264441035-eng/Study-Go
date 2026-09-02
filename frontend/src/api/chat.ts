const API_BASE_URL = "http://127.0.0.1:8000";

export async function sendMessage(message: string) {
  const response = await fetch(
    `${API_BASE_URL}/api/chat/message`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        message,
      }),
    }
  );

  if (!response.ok) {
    throw new Error("メッセージ送信に失敗しました");
  }

  return response.json();
}


export async function getReply() {
  const response = await fetch(
    `${API_BASE_URL}/api/chat/reply`
  );

  if (!response.ok) {
    throw new Error("返信取得に失敗しました");
  }

  return response.json();
}


export async function sendTodayContent(content: string) {
  const response = await fetch(
    `${API_BASE_URL}/api/chat/today`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        content,
      }),
    }
  );

  if (!response.ok) {
    throw new Error("今日の学習内容の送信に失敗しました");
  }

  return response.json();
}


export async function getQuestion() {
  const response = await fetch(
    `${API_BASE_URL}/api/chat/question`
  );

  if (!response.ok) {
    throw new Error("質問取得に失敗しました");
  }

  return response.json();
}


export async function sendExplanation(explanation: string) {
  const response = await fetch(
    `${API_BASE_URL}/api/chat/explanation`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        explanation,
      }),
    }
  );

  if (!response.ok) {
    throw new Error("説明の送信に失敗しました");
  }

  return response.json();
}


export async function getFeedback() {
  const response = await fetch(
    `${API_BASE_URL}/api/chat/feedback`
  );

  if (!response.ok) {
    throw new Error("フィードバック取得に失敗しました");
  }

  return response.json();
}
