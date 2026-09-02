import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import "./style.css";

const API_BASE = import.meta.env.VITE_API_URL ?? "";

// テスト用：実際のキャラクターIDに変更
const characterId = "ここにキャラクターID";

export default function Home() {
  const navigate = useNavigate();

  const [studyTime, setStudyTime] = useState("取得中...");
  const [level, setLevel] = useState("取得中...");

  // キャラクター情報をAPIから取得
  useEffect(() => {
    fetch(`${API_BASE}/api/characters/${characterId}`)
      .then((response) => {
        if (!response.ok) {
          throw new Error(`API error: ${response.status}`);
        }

        return response.json();
      })
      .then((data) => {
        console.log("Character API:", data);

        // 累計勉強時間
        setStudyTime(data.total_study_time);

        // レベル
        setLevel(data.level);
      })
        .catch((error) => {
        console.error("キャラクター情報の取得に失敗:", error);
        setStudyTime("00:00");
        setLevel("1");
        });
  }, []);

  return (
    <main className="home">

      {/* レベル */}
      <h1>
        Lv. <span id="level">{level}</span>
      </h1>

      {/* 累計勉強時間 */}
      <p className="study-time">
        累計勉強時間：
        <span id="studyTime">{studyTime}</span>
      </p>

      {/* キャラの状態など */}
      <p className="status">仮置き</p>

      {/* キャラクター */}
      <div className="character">
        <img
          src="/images/deformed.png"
          alt="キャラクター"
        />
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