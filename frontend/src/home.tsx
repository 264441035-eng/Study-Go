import { useEffect, useState } from "react";
import "./style.css";

const API_BASE = import.meta.env.VITE_API_URL ?? "";

// テスト用：実際のキャラクターIDに変更
const characterId = "aae96c9c-bf1c-4a97-bf29-ab69e7674df8";

export default function Home() {
  const [studyTime, setStudyTime] = useState("取得中...");
  const [level, setLevel] = useState("取得中...");

  // キャラクター情報からレベルを取得
  useEffect(() => {
    fetch(`${API_BASE}/api/characters/${characterId}`)
      .then((response) => {
        if (!response.ok) {
          throw new Error(`Character API error: ${response.status}`);
        }

        return response.json();
      })
      .then((data) => {
        console.log("Character API:", data);

        setLevel(String(data.level ?? 1));
      })
      .catch((error) => {
        console.error("キャラクター情報の取得に失敗:", error);
        setLevel("1");
      });
  }, []);

  // Task APIから勉強時間を取得
  useEffect(() => {
    fetch(`${API_BASE}/api/tasks`)
      .then((response) => {
        if (!response.ok) {
          throw new Error(`Task API error: ${response.status}`);
        }

        return response.json();
      })
      .then((data) => {
        console.log("Task API:", data);

        // APIの仕様が決まったらここを変更
        if (data.total_study_time !== undefined) {
          setStudyTime(String(data.total_study_time));
        } else {
          setStudyTime("00:00");
        }
      })
      .catch((error) => {
        console.error("タスク情報の取得に失敗:", error);
        setStudyTime("00:00");
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

      {/* キャラクターの状態 */}
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
        onClick={() => {
          window.location.hash = "#/study";
        }}
      >
        <img src="/images/study.png" alt="" />
        <span>勉強</span>
      </button>

      {/* 下の3つのボタン */}
      <div className="menu-buttons">
        <button
          className="menu-button chat-button"
          onClick={() => {
            window.location.hash = "#/chat";
          }}
        >
          <img src="/images/chat.png" alt="" />
          <span>チャット</span>
        </button>

        <button
          className="menu-button map-button"
          onClick={() => {
            window.location.hash = "#/map";
          }}
        >
          <img src="/images/map.png" alt="" />
          <span>拠点</span>
        </button>

        <button
          className="menu-button task-button"
          onClick={() => {
            window.location.hash = "#/task";
          }}
        >
          <img src="/images/task.png" alt="" />
          <span>タスク</span>
        </button>
      </div>
    </main>
  );
}