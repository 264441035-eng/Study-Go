import { importLibrary, setOptions } from "@googlemaps/js-api-loader";
import { appearanceForStage } from "./character";

// 本番では VITE_API_URL に ALB の URL を渡す。未設定時は同一オリジンの /api を叩く。
const API_BASE = import.meta.env.VITE_API_URL ?? "";
const GOOGLE_MAPS_API_KEY = import.meta.env.VITE_GOOGLE_MAPS_API_KEY ?? "";

// 拠点がまだ1件も無いときに地図を表示する中心地点（東京駅）。
const DEFAULT_CENTER = { lat: 35.681236, lng: 139.767125 };

// カテゴリごとのピンの色。
const CATEGORY_PIN_COLORS: Record<string, string> = {
    library: "#4a90d9",
    school: "#5cb85c",
    cram_school: "#f0ad4e",
    home: "#9b6bd3",
};
const DEFAULT_PIN_COLOR = "#d9534f";

// カテゴリの表示名。
const CATEGORY_LABELS: Record<string, string> = {
    library: "図書館",
    school: "学校",
    cram_school: "塾",
    home: "自宅",
};

// 自宅・学校は1人1件までなので、既に登録済みならプルダウンで選べなくする。
// （バックエンドにも同じ制限があるので、ここはあくまでUX向上のための先回りチェック）
const SINGLE_INSTANCE_CATEGORIES = new Set(["home", "school"]);

interface Base {
    id: string;
    name: string;
    category: string;
    latitude: string;
    longitude: string;
    total_study_seconds: number;
    level: number;
}

interface LatLng {
    lat: number;
    lng: number;
}

const mapElement = document.getElementById("map") as HTMLDivElement;
const messageElement = document.getElementById("mapMessage") as HTMLParagraphElement;
const countElement = document.getElementById("baseCount") as HTMLSpanElement;
const backButton = document.getElementById("backButton") as HTMLButtonElement;

const startRegisterButton = document.getElementById("startRegisterButton") as HTMLButtonElement;
const mapHintElement = document.getElementById("mapHint") as HTMLParagraphElement;
const baseFormSection = document.getElementById("baseFormSection") as HTMLElement;
const baseForm = document.getElementById("baseForm") as HTMLFormElement;
const nameInput = document.getElementById("baseName") as HTMLInputElement;
const categorySelect = document.getElementById("baseCategory") as HTMLSelectElement;
const selectedLocationElement = document.getElementById("selectedLocation") as HTMLParagraphElement;
const useCurrentLocationButton = document.getElementById(
    "useCurrentLocationButton",
) as HTMLButtonElement;
const cancelRegisterButton = document.getElementById("cancelRegisterButton") as HTMLButtonElement;
const formMessageElement = document.getElementById("formMessage") as HTMLParagraphElement;
const submitButton = document.getElementById("submitButton") as HTMLButtonElement;

let map: google.maps.Map | undefined;
let baseMarkers: google.maps.Marker[] = [];
let infoWindow: google.maps.InfoWindow | undefined;
// ホバーで開いただけの吹き出しはmouseoutで自動的に閉じるが、
// クリックで開いた（削除ボタン付きの）吹き出しは開いたままにしておく。
let infoWindowMode: "hover" | "click" | null = null;

// 「拠点を登録」ボタンを押してから地図をクリックするまでの間だけtrue。
let isRegistering = false;

// クリック（またはドラッグ）で選んだ「これから登録する場所」の仮ピン。
let pendingMarker: google.maps.Marker | undefined;
let pendingLocation: LatLng | undefined;

backButton.addEventListener("click", () => {
    location.href = "index.html";
});

function showMessage(text: string, isError = false): void {
    messageElement.textContent = text;
    messageElement.classList.toggle("error", isError);
}

function showFormMessage(text: string, isError = false): void {
    formMessageElement.textContent = text;
    formMessageElement.classList.toggle("error", isError);
}

async function fetchBases(): Promise<Base[]> {
    const response = await fetch(`${API_BASE}/api/v1/bases`);

    if (!response.ok) {
        throw new Error("拠点の取得に失敗しました");
    }

    return response.json();
}

async function createBase(payload: {
    name: string;
    category: string;
    latitude: number;
    longitude: number;
}): Promise<void> {
    const response = await fetch(`${API_BASE}/api/v1/bases`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
    });

    if (!response.ok) {
        const body = await response.json().catch(() => null);
        throw new Error(body?.detail ?? "拠点の登録に失敗しました");
    }
}

async function deleteBase(id: string): Promise<void> {
    const response = await fetch(`${API_BASE}/api/v1/bases/${id}`, {
        method: "DELETE",
    });

    if (!response.ok && response.status !== 204) {
        throw new Error("拠点の削除に失敗しました");
    }
}

async function handleDeleteBase(base: Base): Promise<void> {
    if (!window.confirm(`「${base.name}」を削除しますか？`)) {
        return;
    }

    infoWindow?.close();
    infoWindowMode = null;

    try {
        await deleteBase(base.id);
        await refreshBases();
    } catch (error) {
        showMessage(error instanceof Error ? error.message : "拠点の削除に失敗しました", true);
    }
}

function formatStudyDuration(totalSeconds: number): string {
    const totalMinutes = Math.floor(totalSeconds / 60);
    const hours = Math.floor(totalMinutes / 60);
    const minutes = totalMinutes % 60;
    return hours === 0 ? `${minutes}分` : `${hours}時間${minutes}分`;
}

function buildBaseStatsElement(base: Base): HTMLParagraphElement {
    const stats = document.createElement("p");
    stats.className = "base-info-stats";
    stats.textContent = `Lv.${base.level}・累計 ${formatStudyDuration(base.total_study_seconds)}`;
    return stats;
}

function buildHoverContent(base: Base): HTMLElement {
    const container = document.createElement("div");
    container.className = "base-info-window";

    const title = document.createElement("p");
    title.className = "base-info-title";
    title.textContent = base.name;
    container.appendChild(title);

    const category = document.createElement("p");
    category.className = "base-info-category";
    category.textContent = CATEGORY_LABELS[base.category] ?? base.category;
    container.appendChild(category);

    container.appendChild(buildBaseStatsElement(base));

    return container;
}

function buildInfoWindowContent(base: Base): HTMLElement {
    const container = document.createElement("div");
    container.className = "base-info-window";

    const title = document.createElement("p");
    title.className = "base-info-title";
    title.textContent = base.name;
    container.appendChild(title);

    const category = document.createElement("p");
    category.className = "base-info-category";
    category.textContent = CATEGORY_LABELS[base.category] ?? base.category;
    container.appendChild(category);

    container.appendChild(buildBaseStatsElement(base));

    const deleteButton = document.createElement("button");
    deleteButton.type = "button";
    deleteButton.className = "base-info-delete-button";
    deleteButton.textContent = "削除する";
    deleteButton.addEventListener("click", () => {
        void handleDeleteBase(base);
    });
    container.appendChild(deleteButton);

    return container;
}

function createPinIcon(color: string): google.maps.Symbol {
    return {
        path: google.maps.SymbolPath.CIRCLE,
        fillColor: color,
        fillOpacity: 1,
        strokeColor: "#ffffff",
        strokeWeight: 2,
        scale: 9,
    };
}

function clearBaseMarkers(): void {
    infoWindow?.close();
    infoWindowMode = null;

    for (const marker of baseMarkers) {
        marker.setMap(null);
    }
    baseMarkers = [];
}

function updateCategoryOptions(bases: Base[]): void {
    const usedSingleCategories = new Set(
        bases.map((base) => base.category).filter((category) => SINGLE_INSTANCE_CATEGORIES.has(category)),
    );

    for (const option of Array.from(categorySelect.options)) {
        const isUsed = usedSingleCategories.has(option.value);
        option.disabled = isUsed;
        option.textContent = isUsed
            ? `${CATEGORY_LABELS[option.value]}（登録済み）`
            : CATEGORY_LABELS[option.value];
    }

    if (categorySelect.selectedOptions[0]?.disabled) {
        const firstEnabled = Array.from(categorySelect.options).find((option) => !option.disabled);
        if (firstEnabled) {
            categorySelect.value = firstEnabled.value;
        }
    }
}

function renderBases(bases: Base[]): void {
    if (!map) {
        return;
    }

    countElement.textContent = String(bases.length);
    updateCategoryOptions(bases);
    clearBaseMarkers();

    const bounds = new google.maps.LatLngBounds();

    for (const base of bases) {
        const position = { lat: Number(base.latitude), lng: Number(base.longitude) };

        const marker = new google.maps.Marker({
            position,
            map,
            title: base.name,
            icon: createPinIcon(CATEGORY_PIN_COLORS[base.category] ?? DEFAULT_PIN_COLOR),
        });

        if (!infoWindow) {
            infoWindow = new google.maps.InfoWindow();
            infoWindow.addListener("closeclick", () => {
                infoWindowMode = null;
            });
        }

        marker.addListener("mouseover", () => {
            if (infoWindowMode === "click") {
                return;
            }
            infoWindow!.setContent(buildHoverContent(base));
            infoWindow!.open({ map, anchor: marker });
            infoWindowMode = "hover";
        });

        marker.addListener("mouseout", () => {
            if (infoWindowMode === "hover") {
                infoWindow!.close();
                infoWindowMode = null;
            }
        });

        marker.addListener("click", () => {
            infoWindow!.setContent(buildInfoWindowContent(base));
            infoWindow!.open({ map, anchor: marker });
            infoWindowMode = "click";
        });

        baseMarkers.push(marker);
        bounds.extend(position);
    }

    if (bases.length === 1) {
        map.setCenter(bounds.getCenter());
        map.setZoom(13);
    } else if (bases.length > 1) {
        map.fitBounds(bounds);
    }

    showMessage(bases.length === 0 ? "拠点がまだ登録されていません。" : "");
}

// =========================
// 現在地に「今の進化段階のキャラ」を描画する
// =========================

let currentLocationMarker: google.maps.Marker | undefined;

// キャラの現在の進化段階を取得する。失敗時は 0（進化前）とする。
async function fetchCharacterStage(): Promise<number> {
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
        return typeof data.evolution_stage === "number"
            ? data.evolution_stage
            : 0;
    } catch (error) {
        console.error("キャラの進化段階の取得に失敗:", error);
        return 0;
    }
}

// 現在地を取得し、進化段階に応じたキャラ画像のマーカーを立てる。
async function showCurrentLocationCharacter(): Promise<void> {
    if (!map || !navigator.geolocation) {
        return;
    }

    const stage = await fetchCharacterStage();
    const appearance = appearanceForStage(stage);

    navigator.geolocation.getCurrentPosition(
        (position) => {
            if (!map) {
                return;
            }
            const location = {
                lat: position.coords.latitude,
                lng: position.coords.longitude,
            };

            currentLocationMarker?.setMap(null);
            currentLocationMarker = new google.maps.Marker({
                position: location,
                map,
                title: "現在地",
                icon: {
                    url: appearance.src,
                    scaledSize: new google.maps.Size(48, 64),
                    anchor: new google.maps.Point(24, 64),
                },
                // 拠点ピンより手前に表示する。
                zIndex: 10000,
            });

            // 拠点が無いときだけ現在地に寄せる（拠点があればそちらの表示を優先）。
            if (baseMarkers.length === 0) {
                map.setCenter(location);
                map.setZoom(15);
            }
        },
        () => {
            // 現在地が取得できなくても地図は使えるので、静かに諦める。
        },
    );
}

async function refreshBases(): Promise<void> {
    try {
        const bases = await fetchBases();
        renderBases(bases);
    } catch (error) {
        countElement.textContent = "-";
        showMessage(error instanceof Error ? error.message : "拠点の取得に失敗しました", true);
    }
}

// =========================
// 登録モード（トリガーボタン→地図クリック→ピンを指す）
// =========================

function formatLocation(location: LatLng): string {
    return `選択した場所：${location.lat.toFixed(6)}, ${location.lng.toFixed(6)}`;
}

function setPendingLocation(location: LatLng): void {
    pendingLocation = location;
    submitButton.disabled = false;

    selectedLocationElement.textContent = formatLocation(location);
    selectedLocationElement.classList.add("selected");

    if (!map) {
        return;
    }

    if (pendingMarker) {
        pendingMarker.setPosition(location);
    } else {
        pendingMarker = new google.maps.Marker({
            position: location,
            map,
            draggable: true,
            animation: google.maps.Animation.DROP,
        });

        pendingMarker.addListener("dragend", () => {
            const position = pendingMarker!.getPosition();
            if (position) {
                setPendingLocation({ lat: position.lat(), lng: position.lng() });
            }
        });
    }
}

function clearPendingLocation(): void {
    pendingLocation = undefined;
    pendingMarker?.setMap(null);
    pendingMarker = undefined;

    selectedLocationElement.textContent = "場所が未選択です";
    selectedLocationElement.classList.remove("selected");
    submitButton.disabled = true;
}

function enterRegisterMode(): void {
    isRegistering = true;

    startRegisterButton.hidden = true;
    mapHintElement.hidden = false;
    baseFormSection.hidden = false;
    mapElement.classList.add("placing");

    showFormMessage("");
}

function exitRegisterMode(): void {
    isRegistering = false;

    startRegisterButton.hidden = false;
    mapHintElement.hidden = true;
    baseFormSection.hidden = true;
    mapElement.classList.remove("placing");

    baseForm.reset();
    clearPendingLocation();
    showFormMessage("");
}

function fillCurrentLocation(): void {
    if (!navigator.geolocation) {
        showFormMessage("この端末では現在地を取得できません。", true);
        return;
    }
    if (!map) {
        return;
    }

    useCurrentLocationButton.disabled = true;
    showFormMessage("現在地を取得中...");

    navigator.geolocation.getCurrentPosition(
        (position) => {
            const location = { lat: position.coords.latitude, lng: position.coords.longitude };
            setPendingLocation(location);
            map!.setCenter(location);
            map!.setZoom(15);
            useCurrentLocationButton.disabled = false;
            showFormMessage("現在地をピンにしました。");
        },
        () => {
            useCurrentLocationButton.disabled = false;
            showFormMessage("現在地の取得に失敗しました。", true);
        },
    );
}

async function handleSubmit(event: SubmitEvent): Promise<void> {
    event.preventDefault();

    if (!nameInput.value.trim()) {
        showFormMessage("拠点名を入力してください。", true);
        return;
    }
    if (!pendingLocation) {
        showFormMessage("地図をクリックして場所を選んでください。", true);
        return;
    }

    submitButton.disabled = true;
    showFormMessage("登録中...");

    try {
        await createBase({
            name: nameInput.value.trim(),
            category: categorySelect.value,
            latitude: pendingLocation.lat,
            longitude: pendingLocation.lng,
        });

        exitRegisterMode();
        await refreshBases();
    } catch (error) {
        showFormMessage(error instanceof Error ? error.message : "拠点の登録に失敗しました", true);
        submitButton.disabled = false;
    }
}

// 勉強終了画面などから「?lat=..&lng=..」付きで遷移してきた場合、
// その場所にピンを指した状態で登録フォームを開く。
function applyPendingLocationFromQuery(): void {
    const params = new URLSearchParams(window.location.search);
    const paramLat = params.get("lat");
    const paramLng = params.get("lng");
    if (paramLat === null || paramLng === null) {
        return;
    }

    const location = { lat: Number(paramLat), lng: Number(paramLng) };
    if (!Number.isFinite(location.lat) || !Number.isFinite(location.lng)) {
        return;
    }

    enterRegisterMode();
    setPendingLocation(location);
    map!.setCenter(location);
    map!.setZoom(15);

    // 再読み込みやブラウザバックで登録モードが再発火しないようURLから消す。
    window.history.replaceState({}, "", window.location.pathname);
}

startRegisterButton.addEventListener("click", enterRegisterMode);
cancelRegisterButton.addEventListener("click", exitRegisterMode);
useCurrentLocationButton.addEventListener("click", fillCurrentLocation);
baseForm.addEventListener("submit", (event) => {
    void handleSubmit(event);
});

async function initPage(): Promise<void> {
    if (!GOOGLE_MAPS_API_KEY) {
        showMessage(
            "Google MapsのAPIキーが未設定です（環境変数 VITE_GOOGLE_MAPS_API_KEY）。",
            true,
        );
        return;
    }

    setOptions({ key: GOOGLE_MAPS_API_KEY, v: "weekly" });
    const { Map } = await importLibrary("maps");

    map = new Map(mapElement, {
        center: DEFAULT_CENTER,
        zoom: 11,
        streetViewControl: false,
        mapTypeControl: false,
    });

    map.addListener("click", (event: google.maps.MapMouseEvent) => {
        if (isRegistering && event.latLng) {
            setPendingLocation({ lat: event.latLng.lat(), lng: event.latLng.lng() });
        }
    });

    await refreshBases();
    void showCurrentLocationCharacter();
    applyPendingLocationFromQuery();
}

initPage();
