import { useNavigate } from "react-router-dom";
import "./chat.css";

export default function Chat() {
  const navigate = useNavigate();

  return (
    <main className="chat-page">

      {/* ヘッダー */}
      <header className="chat-header">
        <button
          className="back-button"
          onClick={() => navigate("/task")}
        >
          ←
        </button>

        <h1>チャット</h1>
      </header>

      {/* チャット画面 */}
      <section className="chat-area">
        <p className="chat-placeholder">
          AIとのチャット画面
        </p>
      </section>

    </main>
  );
}