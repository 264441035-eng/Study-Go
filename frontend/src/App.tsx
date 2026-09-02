import { useState } from "react";

import {
  getFeedback,
  getQuestion,
  getReply,
  sendExplanation,
  sendMessage,
  sendTodayContent,
} from "./api/chat";


type ChatMessage = {
  role: "character" | "user";
  content: string;
};


function App() {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      role: "character",
      content: "今日は何を勉強したの？",
    },
  ]);

  const [input, setInput] = useState("");
  const [mode, setMode] = useState<
    "today" | "explanation" | "message"
  >("today");

  const [loading, setLoading] = useState(false);


  const addMessage = (
    role: "character" | "user",
    content: string
  ) => {
    setMessages((prev) => [
      ...prev,
      {
        role,
        content,
      },
    ]);
  };


  const handleSend = async () => {
    if (!input.trim() || loading) {
      return;
    }

    const text = input.trim();

    setInput("");
    addMessage("user", text);
    setLoading(true);

    try {
      if (mode === "today") {
        await sendTodayContent(text);

        const result = await getQuestion();

        addMessage(
          "character",
          result.message
        );

        setMode("explanation");

      } else if (mode === "explanation") {
        await sendExplanation(text);

        const result = await getFeedback();

        addMessage(
          "character",
          result.message
        );

        setMode("message");

      } else {
        await sendMessage(text);

        const result = await getReply();

        addMessage(
          "character",
          result.message
        );
      }

    } catch (error) {
      console.error(error);

      addMessage(
        "character",
        "エラーが発生しました。もう一度試してみてください。"
      );

    } finally {
      setLoading(false);
    }
  };


  return (
    <div
      style={{
        maxWidth: "800px",
        margin: "0 auto",
        padding: "40px 20px",
      }}
    >
      <h1>Study-Go</h1>

      <h2>学習チャット</h2>


      <div
        style={{
          border: "1px solid #ccc",
          borderRadius: "8px",
          padding: "20px",
          minHeight: "400px",
          marginBottom: "20px",
        }}
      >
        {messages.map((message, index) => (
          <div
            key={index}
            style={{
              textAlign:
                message.role === "user"
                  ? "right"
                  : "left",
              marginBottom: "15px",
            }}
          >
            <div>
              {message.role === "character"
                ? "キャラクター"
                : "あなた"}
            </div>

            <div
              style={{
                display: "inline-block",
                padding: "10px 15px",
                borderRadius: "8px",
                background:
                  message.role === "user"
                    ? "#e0f2ff"
                    : "#f0f0f0",
                maxWidth: "70%",
              }}
            >
              {message.content}
            </div>
          </div>
        ))}

        {loading && (
          <div>
            キャラクターが考えています...
          </div>
        )}
      </div>


      <div
        style={{
          display: "flex",
          gap: "10px",
        }}
      >
        <input
          type="text"
          value={input}
          onChange={(event) =>
            setInput(event.target.value)
          }
          onKeyDown={(event) => {
            if (event.key === "Enter") {
              handleSend();
            }
          }}
          placeholder={
            mode === "today"
              ? "今日勉強したことを入力"
              : mode === "explanation"
              ? "自分の言葉で説明してください"
              : "メッセージを入力"
          }
          style={{
            flex: 1,
            padding: "10px",
          }}
        />

        <button
          onClick={handleSend}
          disabled={loading}
        >
          送信
        </button>
      </div>
    </div>
  );
}

export default App;
