export {};

type TaskCategory = "study" | "exercise";

interface Task {
    id: number;
    title: string;
    completed: boolean;
}




// --------------------
// 仮データ
// API完成後に置き換える
// --------------------

const studyTasks: Task[] = [
    {
        id: 1,
        title: "1時間勉強する",
        completed: false,
    },
    {
        id: 2,
        title: "AIにやったことを説明する",
        completed: false,
    },
    {
        id: 3,
        title: "AIの問題に答える",
        completed: false,
    },
];

const exerciseTasks: Task[] = [
    {
        id: 4,
        title: "拠点まで徒歩で移動する",
        completed: false,
    },
    {
        id: 5,
        title: "散歩する",
        completed: false,
    },
    {
        id: 6,
        title: "スクワットをする",
        completed: false,
    },
];


// --------------------
// 現在選択しているタブ
// --------------------

let currentCategory: TaskCategory = "study";


// --------------------
// HTML要素
// --------------------

const studyTab = document.getElementById(
    "study-tab"
) as HTMLButtonElement;

const exerciseTab = document.getElementById(
    "exercise-tab"
) as HTMLButtonElement;

const categoryTitle = document.getElementById(
    "category-title"
) as HTMLHeadingElement;

const progressText = document.getElementById(
    "progress-text"
) as HTMLSpanElement;

const progressFill = document.getElementById(
    "progress-fill"
) as HTMLDivElement;

const taskList = document.getElementById(
    "task-list"
) as HTMLDivElement;

const backButton = document.getElementById(
    "back-button"
) as HTMLButtonElement;


// --------------------
// 現在のタスクを取得
// --------------------

function getCurrentTasks(): Task[] {
    if (currentCategory === "study") {
        return studyTasks;
    }

    return exerciseTasks;
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

        if (task.completed) {
            taskItem.classList.add("completed");
        }


        const checkbox = document.createElement("div");

        checkbox.className = "task-checkbox";

        if (task.completed) {
            checkbox.textContent = "✓";
        }


        const taskText = document.createElement("span");

        taskText.className = "task-text";
        taskText.textContent = task.title;


        taskItem.appendChild(checkbox);
        taskItem.appendChild(taskText);


        taskItem.addEventListener("click", () => {

            toggleTask(task.id);

        });


        taskList.appendChild(taskItem);

    });

    updateProgress();
}


// --------------------
// タスクの達成状態を変更
// --------------------

function toggleTask(taskId: number): void {

    const tasks = getCurrentTasks();

    const task = tasks.find(
        (task) => task.id === taskId
    );

    if (!task) {
        return;
    }

    task.completed = !task.completed;

    renderTasks();

    /*
     * API完成後：
     *
     * ここでPOST APIを呼び出す
     *
     * 例：
     *
     * await fetch("/api/...", {
     *     method: "POST",
     *     ...
     * });
     */
}


// --------------------
// 達成状況を更新
// --------------------

function updateProgress(): void {

    const tasks = getCurrentTasks();

    const completedCount = tasks.filter(
        (task) => task.completed
    ).length;

    const totalCount = tasks.length;

    progressText.textContent =
        `${completedCount} / ${totalCount}`;

    const percentage =
        totalCount === 0
            ? 0
            : (completedCount / totalCount) * 100;

    progressFill.style.width =
        `${percentage}%`;
}


// --------------------
// タブ切り替え
// --------------------

function switchCategory(
    category: TaskCategory
): void {

    currentCategory = category;


    if (category === "study") {

        studyTab.classList.add("active");
        exerciseTab.classList.remove("active");

        categoryTitle.textContent =
            "今日の勉強";

    } else {

        exerciseTab.classList.add("active");
        studyTab.classList.remove("active");

        categoryTitle.textContent =
            "今日の運動";
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
// 初期表示
// --------------------

renderTasks();