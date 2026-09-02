import { appearanceForStage, evolutionProgress } from "./character";

// 本番では VITE_API_URL に ALB の URL を渡す。未設定時は同一オリジンの /api を叩く。
const API_BASE = import.meta.env.VITE_API_URL ?? "";

const levelElement = document.getElementById("level") as HTMLSpanElement | null;
const studyTimeElement =
    document.getElementById("studyTime") as HTMLSpanElement | null;
const statusElement = document.getElementById("status") as HTMLElement | null;
const characterImage =
    document.getElementById("characterImage") as HTMLImageElement | null;
const xpBarFill =
    document.getElementById("xpBarFill") as HTMLDivElement | null;
const xpLabel = document.getElementById("xpLabel") as HTMLElement | null;
const resetButton =
    document.getElementById("resetButton") as HTMLButtonElement | null;

// リセットボタンから使えるよう、現在のデモ用キャラクターIDを保持する。
let currentCharacterId: string | null = null;

// 進化段階に応じた状態メッセージ。
function statusMessageForStage(stage: number): string {
    if (stage >= 4) {
        return "最終進化を達成！さすが！";
    }
    if (stage >= 1) {
        return "進化した！この調子で続けよう";
    }
    return "勉強してキャラを進化させよう！";
}

// 進化段階に応じてキャラ画像を差し替え、PNGならぴょこぴょこ動かす。
function renderCharacter(stage: number): void {
    if (characterImage === null) {
        return;
    }
    const appearance = appearanceForStage(stage);
    characterImage.src = appearance.src;
    characterImage.classList.toggle("is-bouncing", appearance.bounce);
}

// 経験値（次の進化まで）バーを描画する。
function renderXpBar(level: number, stage: number): void {
    const progress = evolutionProgress(level, stage);

    if (xpBarFill !== null) {
        xpBarFill.style.width = `${Math.round(progress.ratio * 100)}%`;
    }
    if (xpLabel !== null) {
        xpLabel.textContent =
            progress.nextLevel === null
                ? "最終進化に到達"
                : `次の進化まで Lv.${progress.nextLevel}`;
    }
}

// =========================
// キャラの育成状態を取得して描画
// =========================
// ログインのないデモ版では initialize でデモ用キャラを取得（なければ作成）し、
// レベル・進化段階・経験値バーを表示する。
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
        currentCharacterId = characterId;

        // 取得したキャラクターの育成状態を取得する。
        const response = await fetch(
            `${API_BASE}/api/characters/${characterId}`,
        );
        if (!response.ok) {
            throw new Error(`character API error: ${response.status}`);
        }
        const data = await response.json();

        const level: number = data.level;
        const stage: number = data.evolution_stage;

        if (levelElement !== null) {
            levelElement.textContent = String(level);
        }
        renderCharacter(stage);
        renderXpBar(level, stage);
        if (statusElement !== null) {
            statusElement.textContent = statusMessageForStage(stage);
        }
    } catch (error) {
        console.error("キャラクター情報の取得に失敗:", error);
        if (levelElement !== null) {
            levelElement.textContent = "?";
        }
        if (statusElement !== null) {
            statusElement.textContent = "情報の取得に失敗しました";
        }
    }
}

// =========================
// 今日の勉強時間を取得して描画
// =========================
async function loadTodayStudyTime(): Promise<void> {
    if (studyTimeElement === null) {
        return;
    }
    try {
        const response = await fetch(
            `${API_BASE}/api/tasks/context/study-time`,
        );
        if (!response.ok) {
            throw new Error(`study-time API error: ${response.status}`);
        }
        const data = await response.json();
        studyTimeElement.textContent = `${Math.round(data.today_minutes)}分`;
    } catch (error) {
        console.error("今日の勉強時間の取得に失敗:", error);
        studyTimeElement.textContent = "--";
    }
}

// =========================
// デモ用：レベルを初期状態へリセット
// =========================
// リセットAPIを呼んだあと、レベル・経験値バー・今日の勉強時間を再描画する。
async function resetCharacter(): Promise<void> {
    if (currentCharacterId === null) {
        return;
    }
    if (!window.confirm("レベルを初期状態（Lv.1）に戻します。よろしいですか？")) {
        return;
    }
    if (resetButton !== null) {
        resetButton.disabled = true;
    }
    try {
        const response = await fetch(
            `${API_BASE}/api/characters/${currentCharacterId}/reset`,
            { method: "POST" },
        );
        if (!response.ok) {
            throw new Error(`reset API error: ${response.status}`);
        }
        await Promise.all([loadCharacter(), loadTodayStudyTime()]);
    } catch (error) {
        console.error("レベルのリセットに失敗:", error);
        if (statusElement !== null) {
            statusElement.textContent = "リセットに失敗しました";
        }
    } finally {
        if (resetButton !== null) {
            resetButton.disabled = false;
        }
    }
}

resetButton?.addEventListener("click", resetCharacter);

loadCharacter();
loadTodayStudyTime();
