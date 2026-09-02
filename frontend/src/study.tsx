import { useEffect, useState } from "react";
import "./study.css";

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

    // 勉強を終了したらタイマーを止める
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
  const handleStop = () => {
    setIsStudying(false);
    setTodayTime(formatTime(elapsedSeconds));
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
        今日の勉強時間：
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