import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import "./study.css";

const API_BASE = "";

export default function Study() {
  const navigate = useNavigate();

  // キャラクターID
  const [characterId, setCharacterId] = useState<string | null>(null);

  // 勉強中かどうか
  const [isStudying, setIsStudying] = useState(false);

  // 今回の勉強時間（秒）
  const [elapsedSeconds, setElapsedSeconds] = useState(0);

  // 累計勉強時間
  const [studyTime, setStudyTime] = useState("00:00");

  // API通信中かどうか
  const [isSaving, setIsSaving] = useState(false);

  // --------------------------------
  // キャラクターを取得または作成
  // --------------------------------
  useEffect(() => {
    const initializeCharacter = async () => {
      try {
        // デモ用キャラクターを取得または作成
        const response = await fetch(
          `${API_BASE}/api/characters/initialize`,
          {
            method: "POST",
          }
        );

        if (!response.ok) {
          const errorText = await response.text();
          console.error("APIエラー:", errorText);
          throw new Error(`API error: ${response.status}`);
        }

        // APIからキャラクターIDを取得
        const id = await response.json();

        console.log("キャラクターID:", id);

        setCharacterId(id);

        // キャラクター情報を取得
        const characterResponse = await fetch(
          `${API_BASE}/api/characters/${id}`
        );

        if (!characterResponse.ok) {
          throw new Error(
            `API error: ${characterResponse.status}`
          );
        }

        const characterData = await characterResponse.json();

        console.log("キャラクター情報:", characterData);

        // 累計勉強時間を表示
        setStudyTime(
          characterData.total_study_time ?? "00:00"
        );
      } catch (error) {
        console.error(
          "キャラクター情報の取得に失敗:",
          error
        );

        // 取得失敗時は0
        setStudyTime("00:00");
      }
    };

    initializeCharacter();
  }, []);

  // --------------------------------
  // タイマー
  //
  // 勉強中 かつ Study画面が表示されている
  // ときだけ時間を加算
  // --------------------------------
  useEffect(() => {
    if (!isStudying) {
      return;
    }

    const timerId = window.setInterval(() => {
      // 別タブ・別サイト・別アプリなどに
      // 移動している場合は加算しない
      if (document.visibilityState === "visible") {
        setElapsedSeconds((prev) => prev + 1);
      }
    }, 1000);

    return () => {
      window.clearInterval(timerId);
    };
  }, [isStudying]);

  // --------------------------------
  // 勉強開始
  // --------------------------------
  const handleStart = () => {
    setElapsedSeconds(0);
    setIsStudying(true);
  };

  // --------------------------------
  // 勉強終了
  // --------------------------------
  const handleStop = async () => {
    // タイマーを停止
    setIsStudying(false);

    // キャラクターIDがまだ取得できていない場合
    if (!characterId) {
      console.error("キャラクターIDがありません");
      return;
    }

    // 秒 → 分
    const elapsedMinutes = Math.floor(
      elapsedSeconds / 60
    );

    // 1分未満なら保存しない
    if (elapsedMinutes <= 0) {
      return;
    }

    setIsSaving(true);

    try {
      // 勉強時間をAPIへ保存
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
        const errorText = await response.text();
        console.error("勉強時間APIエラー:", errorText);

        throw new Error(
          `API error: ${response.status}`
        );
      }

      const data = await response.json();

      console.log("勉強時間登録成功:", data);

      // APIから返ってきた累計勉強時間を表示
      setStudyTime(
        data.total_study_time ?? "00:00"
      );

      // 今回の勉強時間をリセット
      setElapsedSeconds(0);

    } catch (error) {
      console.error(
        "勉強時間の登録に失敗:",
        error
      );

      // API保存失敗時は0
      setStudyTime("00:00");

    } finally {
      setIsSaving(false);
    }
  };

  // --------------------------------
  // 秒を HH:MM:SS に変換
  // --------------------------------
  const formatTime = (seconds: number) => {
    const hours = Math.floor(
      seconds / 3600
    );

    const minutes = Math.floor(
      (seconds % 3600) / 60
    );

    const secs = seconds % 60;

    return `${String(hours).padStart(
      2,
      "0"
    )}:${String(minutes).padStart(
      2,
      "0"
    )}:${String(secs).padStart(
      2,
      "0"
    )}`;
  };

  // --------------------------------
  // ホームに戻る
  // --------------------------------
  const handleBack = () => {
    navigate("/");
  };

  return (
    <main className="study-page">

      <h1>勉強</h1>

      <p id="status">
        {isStudying
          ? "勉強中..."
          : "勉強を始めよう！"}
      </p>

      {/* 今回の勉強時間 */}
      <div id="timer">
        {formatTime(elapsedSeconds)}
      </div>

      {/* 勉強していないときだけ表示 */}
      {!isStudying && (
        <button
          id="startButton"
          className="study-start-button"
          onClick={handleStart}
          disabled={isSaving || !characterId}
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
          disabled={isSaving}
        >
          {isSaving
            ? "保存中..."
            : "勉強終了"}
        </button>
      )}

      {/* 累計勉強時間 */}
      <p className="today-time">
        累計勉強時間：
        <span id="todayTime">
          {isSaving
            ? "保存中..."
            : studyTime}
        </span>
      </p>

      {/* ホームに戻る */}
      {/* 勉強していないときだけホームに戻るボタンを表示 */}
{!isStudying && (
  <button
    className="study-back-button"
    id="backButton"
    onClick={handleBack}
    disabled={isSaving}
  >
    ホームに戻る
  </button>
    )}

    </main>
  );
}