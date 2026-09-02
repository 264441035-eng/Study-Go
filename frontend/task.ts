export {};

// 本番では VITE_API_URL に ALB の URL を渡す。未設定時は同一オリジンの /api を叩く。
const API_BASE = import.meta.env.VITE_API_URL ?? "";

type TaskCategory = "study" | "exercise";

interface Task {
    id: number;
    title: string;
    done: boolean;
}

// APIから取得したタスク（完了状態は done）。
let studyTasks: Task[] = [];
let exerciseTasks: Task[] = [];

// 現在選択しているタブ
let currentCategory: TaskCategory = "study";


// --------------------
// HTML要素
// --------------------

const studyTab = document.getElementById("study-tab") as HTMLButtonElement;
const exerciseTab = document.getElementById("exercise-tab") as HTMLButtonElement;
const categoryTitle = document.getElementById(
    "category-title",
) as HTMLHeadingElement;
const progressText = document.getElementById(
    "progress-text",
) as HTMLSpanElement;
const progressFill = document.getElementById(
    "progress-fill",
) as HTMLDivElement;
const taskList = document.getElementById("task-list") as HTMLDivElement;
const taskMessage = document.getElementById(
    "task-message",
) as HTMLParagraphElement;
const backButton = document.getElementById("back-button") as HTMLButtonElement;
const resetButton = document.getElementById(
    "reset-button",
) as HTMLButtonElement | null;


// --------------------
// データ取得
// --------------------

// タスクの表示可否はレベル依存なので、まずキャラのレベルを取得する。
// 失敗時はレベル1として扱う。
async function fetchCharacterLevel(): Promise<number> {
    try {
        const initResponse = await fetch(
            `${API_BASE}/api/characters/initialize`,
            { method: "POST" },
        );
        if (!initResponse.ok) {
            throw new Error(`initialize API error: ${initResponse.status}`);
        }
        const characterId: string = await initResponse.json();

        const response = await fetch(
            `${API_BASE}/api/characters/${characterId}`,
        );
        if (!response.ok) {
            throw new Error(`character API error: ${response.status}`);
        }
        const data = await response.json();
        return typeof data.level === "number" ? data.level : 1;
    } catch (error) {
        console.error("レベルの取得に失敗:", error);
        return 1;
    }
}

async function fetchTasks(
    category: TaskCategory,
    level: number,
): Promise<Task[]> {
    const response = await fetch(
        `${API_BASE}/api/tasks/${category}?level=${level}`,
    );
    if (!response.ok) {
        throw new Error(`${category} tasks API error: ${response.status}`);
    }
    const data = await response.json();
    return data.map((task: { id: number; title: string; done: boolean }) => ({
        id: task.id,
        title: task.title,
        done: task.done,
    }));
}

async function loadTasks(): Promise<void> {
    const level = await fetchCharacterLevel();
    try {
        const [study, exercise] = await Promise.all([
            fetchTasks("study", level),
            fetchTasks("exercise", level),
        ]);
        studyTasks = study;
        exerciseTasks = exercise;
    } catch (error) {
        console.error("タスクの取得に失敗:", error);
        showMessage("タスクの取得に失敗しました", true);
    }
    renderTasks();
}


// --------------------
// 現在のタスクを取得
// --------------------

function getCurrentTasks(): Task[] {
    return currentCategory === "study" ? studyTasks : exerciseTasks;
}


// --------------------
// 一時メッセージ
// --------------------

let messageTimer: number | null = null;

function showMessage(text: string, isError = false): void {
    taskMessage.textContent = text;
    taskMessage.classList.toggle("error", isError);
    taskMessage.hidden = false;

    if (messageTimer !== null) {
        clearTimeout(messageTimer);
    }
    messageTimer = window.setTimeout(() => {
        taskMessage.hidden = true;
    }, 2500);
}


// --------------------
// タスク表示
// --------------------

function renderTasks(): void {
    const tasks = getCurrentTasks();
    taskList.innerHTML = "";

    if (tasks.length === 0) {
        const emptyMessage = document.createElement("div");
        emptyMessage.className = "empty-message";
        emptyMessage.textContent = "タスクはありません。";
        taskList.appendChild(emptyMessage);
        updateProgress();
        return;
    }

    tasks.forEach((task) => {
        const taskItem = document.createElement("div");
        taskItem.className = "task-item";
        if (task.done) {
            taskItem.classList.add("completed");
        }

        const checkbox = document.createElement("div");
        checkbox.className = "task-checkbox";
        if (task.done) {
            checkbox.textContent = "✓";
        }

        const taskText = document.createElement("span");
        taskText.className = "task-text";
        taskText.textContent = task.title;

        taskItem.appendChild(checkbox);
        taskItem.appendChild(taskText);

        taskItem.addEventListener("click", () => {
            void toggleTask(task);
        });

        taskList.appendChild(taskItem);
    });

    updateProgress();
}


// --------------------
// タスクの達成状態を変更（バックエンドへ送信）
// --------------------

async function toggleTask(task: Task): Promise<void> {
    const nextDone = !task.done;

    try {
        const response = await fetch(
            `${API_BASE}/api/tasks/${currentCategory}/${task.id}/status`,
            {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ done: nextDone }),
            },
        );
        if (!response.ok) {
            throw new Error(`status API error: ${response.status}`);
        }

        task.done = nextDone;
        renderTasks();

        // 未完了→完了のときだけ経験値が入る。
        if (nextDone) {
            showMessage("経験値を獲得！ホームで確認しよう ✨");
        }
    } catch (error) {
        console.error("タスクの更新に失敗:", error);
        showMessage("更新に失敗しました", true);
    }
}


// --------------------
// 達成状況を更新
// --------------------

function updateProgress(): void {
    const tasks = getCurrentTasks();
    const completedCount = tasks.filter((task) => task.done).length;
    const totalCount = tasks.length;

    progressText.textContent = `${completedCount} / ${totalCount}`;

    const percentage =
        totalCount === 0 ? 0 : (completedCount / totalCount) * 100;
    progressFill.style.width = `${percentage}%`;
}


// --------------------
// タブ切り替え
// --------------------

function switchCategory(category: TaskCategory): void {
    currentCategory = category;

    if (category === "study") {
        studyTab.classList.add("active");
        exerciseTab.classList.remove("active");
        categoryTitle.textContent = "今日の勉強";
    } else {
        exerciseTab.classList.add("active");
        studyTab.classList.remove("active");
        categoryTitle.textContent = "今日の運動";
    }

    renderTasks();
}


// --------------------
// イベント
// --------------------

studyTab.addEventListener("click", () => {
    switchCategory("study");
});

exerciseTab.addEventListener("click", () => {
    switchCategory("exercise");
});

backButton.addEventListener("click", () => {
    window.location.href = "index.html";
});


// --------------------
// デモ用：タスクの完了状態をリセット
// --------------------

// リセットAPIを呼んだあと、タスク一覧を取り直して再描画する。
async function resetTasks(): Promise<void> {
    if (!window.confirm("全タスクの完了状態を未完了に戻します。よろしいですか？")) {
        return;
    }
    if (resetButton !== null) {
        resetButton.disabled = true;
    }
    try {
        const response = await fetch(`${API_BASE}/api/tasks/reset`, {
            method: "POST",
        });
        if (!response.ok) {
            throw new Error(`reset API error: ${response.status}`);
        }
        await loadTasks();
        showMessage("タスクをリセットしました");
    } catch (error) {
        console.error("タスクのリセットに失敗:", error);
        showMessage("リセットに失敗しました", true);
    } finally {
        if (resetButton !== null) {
            resetButton.disabled = false;
        }
    }
}

resetButton?.addEventListener("click", () => {
    void resetTasks();
});


// --------------------
// 初期表示
// --------------------

renderTasks();
void loadTasks();
