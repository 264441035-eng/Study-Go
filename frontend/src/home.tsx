import "./style.css";
import { useNavigate } from "react-router-dom";

export default function Home() {
  const navigate = useNavigate();

  return (
    <main className="home">

      {/* レベル */}
      <h1>
        Lv. <span id="level">レベルを取得</span>
      </h1>

      {/* 今日の勉強時間 */}
      <p className="study-time">
        今日の勉強時間：
        <span id="studyTime">勉強時間を取得</span>
      </p>

      {/* キャラの状態など */}
      <p className="status">仮置き</p>

      {/* キャラクター */}
      <div className="character">
        <img src="/images/deformed.png" alt="キャラクター" />
      </div>

      {/* 勉強ボタン */}
      <button
        className="study-button"
        onClick={() => navigate("/study")}
      >
        <img src="/images/study.png" alt="" />
        <span>勉強</span>
      </button>

      {/* 下の4つのボタン */}
      <div className="menu-buttons">

        <button
          className="menu-button chat-button"
          onClick={() => navigate("/chat")}
        >
          <img src="/images/chat.png" alt="" />
          <span>チャット</span>
        </button>

        <button
          className="menu-button map-button"
          onClick={() => navigate("/map")}
        >
          <img src="/images/map.png" alt="" />
          <span>拠点</span>
        </button>

        <button
          className="menu-button task-button"
          onClick={() => navigate("/task")}
        >
          <img src="/images/task.png" alt="" />
          <span>タスク</span>
        </button>

        <button
          className="menu-button pass-button"
          onClick={() => navigate("/pass")}
        >
          <img src="/images/pass.png" alt="" />
          <span>すれちがい</span>
        </button>

      </div>

    </main>
  );
}