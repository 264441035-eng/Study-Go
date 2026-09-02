export {};
let startTime: number | null = null;
let timerInterval: number | null = null;
let elapsedSeconds = 0;

const timer = document.getElementById("timer") as HTMLDivElement;
const statusElement =
    document.getElementById("status") as HTMLParagraphElement;
const startButton =
    document.getElementById("startButton") as HTMLButtonElement;

const stopButton =
    document.getElementById("stopButton") as HTMLButtonElement;

stopButton.style.display = "none";

const todayTime =
    document.getElementById("todayTime") as HTMLSpanElement;

const backButton =
    document.getElementById("backButton") as HTMLButtonElement;


// 最初は勉強終了ボタンを非表示
stopButton.style.display = "none";


// =========================
// 時間を HH:MM:SS に変換
// =========================

function formatTime(seconds: number): string {

    const hours = Math.floor(seconds / 3600);

    const minutes =
        Math.floor((seconds % 3600) / 60);

    const secs = seconds % 60;

    return (
        String(hours).padStart(2, "0") +
        ":" +
        String(minutes).padStart(2, "0") +
        ":" +
        String(secs).padStart(2, "0")
    );
}


// =========================
// 勉強開始
// =========================

function startStudy(): void {
    startTime = Date.now();
    elapsedSeconds = 0;

    timer.textContent = "00:00:00";
    statusElement.textContent = "勉強中…";

    // 勉強開始ボタンを非表示
    startButton.style.display = "none";

    // 勉強終了ボタンを表示
    stopButton.style.display = "block";

    timerInterval = window.setInterval(() => {
        if (startTime === null) {
            return;
        }

        elapsedSeconds = Math.floor(
            (Date.now() - startTime) / 1000
        );

        timer.textContent = formatTime(elapsedSeconds);
    }, 1000);
}

// =========================
// 勉強終了
// =========================

function stopStudy(): void {
    if (startTime === null) {
        return;
    }
    const endTime = Date.now();

    const studyTime = Math.floor(
        (endTime - startTime) / 1000
    );
    if (timerInterval !== null) {
        clearInterval(timerInterval);
        timerInterval = null;
    }

    statusElement.textContent = "お疲れさま！";

    // 勉強開始ボタンを表示
    startButton.style.display = "block";

    // 勉強終了ボタンを非表示
    stopButton.style.display = "none";

    console.log(
        "今回の勉強時間：",
        elapsedSeconds,
        "秒"
    );
}
/*
     * 後でバックエンドと接続する場所
     *
     * 例：
     *
     * await fetch("/api/study/end", {
     *     method: "POST",
     *     headers: {
     *         "Content-Type": "application/json"
     *     },
     *     body: JSON.stringify({
     *         studyTime: studySeconds
     *     })
     * });
     */



// =========================
// 今日の勉強時間
// =========================

async function loadTodayStudyTime(): Promise<void> {

    /*
     * 後でバックエンドから取得
     *
     * const response = await fetch("/api/study/today");
     * const data = await response.json();
     *
     * todayTime.textContent =
     *     formatTime(data.studyTime);
     */


    // 現在は仮表示
    todayTime.textContent = "0分";
}


// =========================
// イベント
// =========================

startButton.addEventListener(
    "click",
    startStudy
);

stopButton.addEventListener(
    "click",
    stopStudy
);

backButton.addEventListener(
    "click",
    () => {
        location.href = "index.html";
    }
);


// ページ読み込み時
loadTodayStudyTime();