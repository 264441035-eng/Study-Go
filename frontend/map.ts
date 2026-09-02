import { importLibrary, setOptions } from "@googlemaps/js-api-loader";

// 本番では VITE_API_URL に ALB の URL を渡す。未設定時は同一オリジンの /api を叩く。
const API_BASE = import.meta.env.VITE_API_URL ?? "";
const GOOGLE_MAPS_API_KEY = import.meta.env.VITE_GOOGLE_MAPS_API_KEY ?? "";

// ログイン機能が実装されたら、そこで発行したJWTをここに保存する想定。
const TOKEN_STORAGE_KEY = "studyGoToken";

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

interface Base {
    id: string;
    name: string;
    category: string;
    latitude: string;
    longitude: string;
}

const mapElement = document.getElementById("map") as HTMLDivElement;
const messageElement = document.getElementById("mapMessage") as HTMLParagraphElement;
const countElement = document.getElementById("baseCount") as HTMLSpanElement;
const backButton = document.getElementById("backButton") as HTMLButtonElement;

backButton.addEventListener("click", () => {
    location.href = "index.html";
});

function showMessage(text: string, isError = false): void {
    messageElement.textContent = text;
    messageElement.classList.toggle("error", isError);
}

async function fetchBases(): Promise<Base[]> {
    const token = localStorage.getItem(TOKEN_STORAGE_KEY);
    if (!token) {
        throw new Error("ログインが必要です");
    }

    const response = await fetch(`${API_BASE}/api/v1/bases`, {
        headers: { Authorization: `Bearer ${token}` },
    });

    if (response.status === 401 || response.status === 403) {
        throw new Error("ログインが必要です");
    }
    if (!response.ok) {
        throw new Error("拠点の取得に失敗しました");
    }

    return response.json();
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

async function initMap(): Promise<void> {
    if (!GOOGLE_MAPS_API_KEY) {
        showMessage(
            "Google MapsのAPIキーが未設定です（環境変数 VITE_GOOGLE_MAPS_API_KEY）。",
            true,
        );
        return;
    }

    let bases: Base[];
    try {
        bases = await fetchBases();
    } catch (error) {
        countElement.textContent = "-";
        showMessage(error instanceof Error ? error.message : "拠点の取得に失敗しました", true);
        return;
    }

    countElement.textContent = String(bases.length);

    setOptions({ key: GOOGLE_MAPS_API_KEY, v: "weekly" });
    const { Map } = await importLibrary("maps");

    const center =
        bases.length > 0
            ? { lat: Number(bases[0].latitude), lng: Number(bases[0].longitude) }
            : DEFAULT_CENTER;

    const map = new Map(mapElement, {
        center,
        zoom: bases.length > 0 ? 13 : 11,
    });

    const bounds = new google.maps.LatLngBounds();

    for (const base of bases) {
        const position = { lat: Number(base.latitude), lng: Number(base.longitude) };

        new google.maps.Marker({
            position,
            map,
            title: base.name,
            icon: createPinIcon(CATEGORY_PIN_COLORS[base.category] ?? DEFAULT_PIN_COLOR),
        });

        bounds.extend(position);
    }

    if (bases.length > 1) {
        map.fitBounds(bounds);
    }

    if (bases.length === 0) {
        showMessage("拠点がまだ登録されていません。");
    }
}

initMap();
