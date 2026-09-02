import { useState } from "react";
import { useNavigate } from "react-router-dom";
import "./task.css";

type TaskCategory = "study" | "exercise";

export default function Task() {
  const navigate = useNavigate();

  // 現在選択しているタブ
  const [category, setCategory] = useState<TaskCategory>("study");

  // 仮のタスク
  // APIができたらここをAPI取得に変更する
  const studyTasks = [
    "1時間勉強する",
    "AIにやったことを説明する",
    "AIの問題に答える",
  ];

  const exerciseTasks = [
    "拠点まで徒歩で移動",
    "散歩",
    "スクワット",
  ];

  const tasks =
    category === "study" ? studyTasks : exerciseTasks;

  return (
    <main className="task-page">

      {/* ヘッダー */}
      <header className="task-header">
        <button
          id="back-button"
          className="back-button"
          onClick={() => navigate("/")}
        >
          ←
        </button>

        <h1>タスク</h1>
      </header>

      {/* 勉強 / 運動 タブ */}
      <div className="tabs">
        <button
          id="study-tab"
          className={`tab ${category === "study" ? "active" : ""}`}
          onClick={() => setCategory("study")}
        >
          勉強
        </button>

        <button
          id="exercise-tab"
          className={`tab ${
            category === "exercise" ? "active" : ""
          }`}
          onClick={() => setCategory("exercise")}
        >
          運動
        </button>
      </div>

      {/* 達成状況 */}
      <section className="progress-section">
        <div className="progress-header">
          <h2>
            {category === "study" ? "今日の勉強" : "今日の運動"}
          </h2>

          <span>
            0 / {tasks.length}
          </span>
        </div>

        <div className="progress-bar">
          <div
            className="progress-fill"
            style={{ width: "0%" }}
          />
        </div>
      </section>

      {/* タスク一覧 */}
<section className="task-list-section">
  <div className="task-list">
    {tasks.map((task, index) => {
      const isChatTask =
        task === "AIにやったことを説明する" ||
        task === "AIの問題に答える";

      return (
        <div
          className={`task-item ${isChatTask ? "clickable" : ""}`}
          key={index}
          onClick={() => {
            if (isChatTask) {
              navigate("/chat");
            }
          }}
        >
          <span className="task-text">
            {task}
          </span>

          {isChatTask && (
            <span className="task-arrow">→</span>
          )}
        </div>
      );
    })}
  </div>
</section>
    </main>
  );
}