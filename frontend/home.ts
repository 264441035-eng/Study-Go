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
const speechBubble =
    document.getElementById("speechBubble") as HTMLElement | null;
const bubbleText =
    document.getElementById("bubbleText") as HTMLElement | null;

// 進化段階ごとのキャラのセリフ候補。
// 進化前(stage 0)はツンデレ系の応援、進化後(stage>=1)はお姉さん系（少し上から目線）。
const TSUNDERE_LINES = [
    "もうちょっと頑張りなさいよ！ 私が応援してるんだからね！",
    "べ、別にあなたのために言ってるんじゃないんだからね！",
    "そんなペースで進化できると思ってるの？ ほら、勉強勉強！",
    "…ちょっとはやる気出しなさいよね。見ててあげるから。",
    "サボってない？ 私がいないとダメなんだから、もう。",
];

const ONEE_LINES = [
    "なかなかやるじゃない。この調子で行くといいわ。",
    "ふふ、成長したわね。でも油断は禁物よ？",
    "その調子。あなたならもっと上を目指せるわ。",
    "いい集中力ね。私が見込んだだけのことはあるわ。",
    "少し休んでもいいのよ？ 無理は禁物だからね。",
];

// タイピング演出のタイマー。再描画のたびに前のタイピングを止めるため保持する。
let typingTimer: number | null = null;
// 5秒ごとにセリフを切り替えるためのタイマー。
let bubbleRotationTimer: number | null = null;
// 直前に表示したセリフ。連続で同じものを出さないために覚えておく。
let lastBubbleLine: string | null = null;

// 吹き出しにセリフを1文字ずつ表示する（タイピング風）。
function typewriteBubble(text: string): void {
    if (speechBubble === null || bubbleText === null) {
        return;
    }
    if (typingTimer !== null) {
        window.clearInterval(typingTimer);
    }
    bubbleText.textContent = "";
    speechBubble.classList.add("is-typing");

    let index = 0;
    typingTimer = window.setInterval(() => {
        // Array.from で絵文字などのサロゲートペアも1文字として扱う。
        const chars = Array.from(text);
        bubbleText.textContent = chars.slice(0, index + 1).join("");
        index += 1;
        if (index >= chars.length) {
            if (typingTimer !== null) {
                window.clearInterval(typingTimer);
                typingTimer = null;
            }
            speechBubble.classList.remove("is-typing");
        }
    }, 55);
}

// 進化段階に応じたセリフ候補から、直前と違うものをランダムに1つ選ぶ。
function pickBubbleLine(stage: number): string {
    const lines = stage >= 1 ? ONEE_LINES : TSUNDERE_LINES;
    if (lines.length <= 1) {
        return lines[0];
    }
    let line = lastBubbleLine;
    while (line === lastBubbleLine) {
        line = lines[Math.floor(Math.random() * lines.length)];
    }
    lastBubbleLine = line;
    return line;
}

// 進化段階に応じてセリフを表示し、以降5秒ごとに自動で切り替える。
function showBubbleForStage(stage: number): void {
    // 再読み込み（リセット後など）に備えて、前回のローテーションを止める。
    if (bubbleRotationTimer !== null) {
        window.clearInterval(bubbleRotationTimer);
    }
    lastBubbleLine = null;

    typewriteBubble(pickBubbleLine(stage));

    bubbleRotationTimer = window.setInterval(() => {
        typewriteBubble(pickBubbleLine(stage));
    }, 5000);
}

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
        showBubbleForStage(stage);
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
