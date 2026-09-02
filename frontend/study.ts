export {};

// 本番では VITE_API_URL に ALB の URL を渡す。未設定時は同一オリジンの /api を叩く。
const API_BASE = import.meta.env.VITE_API_URL ?? "";

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
    const minutes = Math.floor((seconds % 3600) / 60);
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

async function startStudy(): Promise<void> {
    // バックエンドへ勉強開始を宣言する。
    // 既にセッションが開始済み(409)でも、そのまま計測を続ける。
    try {
        const response = await fetch(
            `${API_BASE}/api/tasks/study/start`,
            { method: "POST" },
        );
        if (!response.ok && response.status !== 409) {
            throw new Error(`study/start API error: ${response.status}`);
        }
    } catch (error) {
        console.error("勉強開始の送信に失敗:", error);
        statusElement.textContent = "通信エラー。時間は記録されない場合があります";
    }

    startTime = Date.now();
    elapsedSeconds = 0;

    timer.textContent = "00:00:00";
    statusElement.textContent = "勉強中…";

    startButton.style.display = "none";
    stopButton.style.display = "block";

    timerInterval = window.setInterval(() => {
        if (startTime === null) {
            return;
        }
        elapsedSeconds = Math.floor((Date.now() - startTime) / 1000);
        timer.textContent = formatTime(elapsedSeconds);
    }, 1000);
}


// =========================
// 現在地取得
// =========================

// 拠点への勉強時間加算に使う現在地を取得する。
// 取得できない・拒否された場合はnullを返し、位置情報なしで送信する。
function getCurrentPosition(): Promise<GeolocationPosition | null> {
    if (!navigator.geolocation) {
        return Promise.resolve(null);
    }

    return new Promise((resolve) => {
        navigator.geolocation.getCurrentPosition(
            (position) => resolve(position),
            () => resolve(null),
            { timeout: 5000 },
        );
    });
}


// =========================
// 勉強終了
// =========================

async function stopStudy(): Promise<void> {
    if (startTime === null) {
        return;
    }

    if (timerInterval !== null) {
        clearInterval(timerInterval);
        timerInterval = null;
    }

    const studiedSeconds = elapsedSeconds;
    startTime = null;

    startButton.style.display = "block";
    stopButton.style.display = "none";

    // 0秒は送信しない（バックエンドは seconds > 0 を要求する）。
    if (studiedSeconds <= 0) {
        statusElement.textContent = "お疲れさま！";
        return;
    }

    // 勉強時間をバックエンドへ送信する。分単位で経験値（レベル）が上がる。
    // 現在地が取れれば、最寄りの拠点（200m以内）にも勉強時間が加算される。
    const position = await getCurrentPosition();

    try {
        const response = await fetch(
            `${API_BASE}/api/tasks/study/time`,
            {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    seconds: studiedSeconds,
                    ...(position && {
                        latitude: position.coords.latitude,
                        longitude: position.coords.longitude,
                    }),
                }),
            },
        );
        if (!response.ok) {
            throw new Error(`study/time API error: ${response.status}`);
        }
        const data = await response.json();

        const gainedMinutes = Math.floor(studiedSeconds / 60);
        if (gainedMinutes >= 1) {
            statusElement.textContent = data.matched_base_id
                ? `お疲れさま！${gainedMinutes}分ぶんの経験値を獲得！拠点${data.base_leveled_up ? "もレベルアップ！" : "にも記録したよ"}`
                : `お疲れさま！${gainedMinutes}分ぶんの経験値を獲得！ホームで確認しよう`;
        } else {
            statusElement.textContent =
                "お疲れさま！（1分以上で経験値がたまるよ）";
        }

        // 今日の勉強時間を更新表示する。
        await loadTodayStudyTime();

        // 現在地は取れたが拠点にマッチしなかった場合、その場を拠点登録できないか案内する。
        if (position && !data.matched_base_id) {
            const shouldRegister = window.confirm(
                "拠点が登録されていません。現在地を拠点として登録しますか？",
            );
            if (shouldRegister) {
                const { latitude, longitude } = position.coords;
                window.location.href =
                    `map.html?lat=${latitude}&lng=${longitude}`;
            }
        }
    } catch (error) {
        console.error("勉強時間の送信に失敗:", error);
        statusElement.textContent = "お疲れさま！（時間の記録に失敗しました）";
    }
}


// =========================
// 今日の勉強時間
// =========================

async function loadTodayStudyTime(): Promise<void> {
    try {
        const response = await fetch(
            `${API_BASE}/api/tasks/context/study-time`,
        );
        if (!response.ok) {
            throw new Error(`study-time API error: ${response.status}`);
        }
        const data = await response.json();
        todayTime.textContent = `${Math.round(data.today_minutes)}分`;
    } catch (error) {
        console.error("今日の勉強時間の取得に失敗:", error);
        todayTime.textContent = "--";
    }
}


// =========================
// イベント
// =========================

startButton.addEventListener("click", () => {
    void startStudy();
});

stopButton.addEventListener("click", () => {
    void stopStudy();
});

backButton.addEventListener("click", () => {
    location.href = "index.html";
});


// ページ読み込み時
void loadTodayStudyTime();
