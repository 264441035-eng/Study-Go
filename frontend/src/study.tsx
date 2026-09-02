import { useEffect, useState } from "react";
import "./study.css";

const API_BASE = import.meta.env.VITE_API_URL ?? "";

// TODO: 本来はログイン中のキャラクターIDなどから取得する
const characterId = "ここにキャラクターID";

export default function Study() {
  // 勉強中かどうか
  const [isStudying, setIsStudying] = useState(false);

  // 勉強開始からの経過時間（秒）
  const [elapsedSeconds, setElapsedSeconds] = useState(0);

  const [todayTime, setTodayTime] = useState("取得中...");

  // 勉強中だけタイマーを動かす
  useEffect(() => {
    if (!isStudying) {
      return;
    }

    const timerId = window.setInterval(() => {
      setElapsedSeconds((prev) => prev + 1);
    }, 1000);

    return () => {
      window.clearInterval(timerId);
    };
  }, [isStudying]);

  // 勉強開始
  const handleStart = () => {
    setElapsedSeconds(0);
    setIsStudying(true);
  };

  // 勉強終了
  const handleStop = async () => {
    setIsStudying(false);

    // 秒 → 分
    const elapsedMinutes = Math.floor(elapsedSeconds / 60);

    try {
      const response = await fetch(
        `${API_BASE}/api/characters/${characterId}/study`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            minutes: elapsedMinutes,
          }),
        }
      );

      if (!response.ok) {
        throw new Error("勉強時間の登録に失敗しました");
      }

      const data = await response.json();

      // APIから返ってきた勉強時間を表示
      setTodayTime(data.total_study_time);
    } catch (error) {
      console.error(error);
      setTodayTime("取得失敗");
    }
  };

  // 秒を HH:MM:SS に変換
  const formatTime = (seconds: number) => {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = seconds % 60;

    return `${String(hours).padStart(2, "0")}:${String(minutes).padStart(
      2,
      "0"
    )}:${String(secs).padStart(2, "0")}`;
  };

  // ホームに戻る
  const handleBack = () => {
    window.location.href = "/";
  };

  return (
    <main className="study-page">

      <h1>勉強</h1>

      <p id="status">
        {isStudying ? "勉強中..." : "勉強を始めよう！"}
      </p>

      <div id="timer">
        {formatTime(elapsedSeconds)}
      </div>

      {/* 勉強していないときだけ表示 */}
      {!isStudying && (
        <button
          id="startButton"
          className="study-start-button"
          onClick={handleStart}
        >
          勉強開始
        </button>
      )}

      {/* 勉強中だけ表示 */}
      {isStudying && (
        <button
          id="stopButton"
          className="study-stop-button"
          onClick={handleStop}
        >
          勉強終了
        </button>
      )}

      <p className="today-time">
        累計勉強時間：
        <span id="todayTime">{todayTime}</span>
      </p>

      <button
        className="study-back-button"
        id="backButton"
        onClick={handleBack}
      >
        ホームに戻る
      </button>

    </main>
  );
}