export {};

// 本番では VITE_API_URL に ALB の URL を渡す。未設定時は同一オリジンの /api を叩く。
const API_BASE = import.meta.env.VITE_API_URL ?? "";

const levelElement = document.getElementById("level") as HTMLSpanElement | null;
const studyTimeElement =
    document.getElementById("studyTime") as HTMLSpanElement | null;

// =========================
// ホーム画面のキャラ情報を取得
// =========================
// ログインのないデモ版では initialize でデモ用キャラを取得（なければ作成）し、
// そのレベルと累計勉強時間を表示する。
async function loadCharacter(): Promise<void> {
    try {
        // 先頭のキャラクターID（なければ作成）を取得する。
        const initResponse = await fetch(
            `${API_BASE}/api/characters/initialize`,
            { method: "POST" },
        );
        if (!initResponse.ok) {
            throw new Error(`initialize API error: ${initResponse.status}`);
        }
        const characterId: string = await initResponse.json();

        // 取得したキャラクターの育成状態を取得する。
        const response = await fetch(
            `${API_BASE}/api/characters/${characterId}`,
        );
        if (!response.ok) {
            throw new Error(`character API error: ${response.status}`);
        }
        const data = await response.json();

        if (levelElement !== null) {
            levelElement.textContent = String(data.level);
        }
        // TODO: 「今日の勉強時間」は Task API と紐づける予定。
        // 現状は Character API の累計勉強時間（時間:分）を表示する。
        if (studyTimeElement !== null) {
            studyTimeElement.textContent = data.total_study_time;
        }
    } catch (error) {
        console.error("キャラクター情報の取得に失敗:", error);
        if (levelElement !== null) {
            levelElement.textContent = "取得失敗";
        }
        if (studyTimeElement !== null) {
            studyTimeElement.textContent = "--:--";
        }
    }
}

loadCharacter();
