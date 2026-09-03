// AI Tutor Service クライアント。
// Frontend は自前バックエンドを経由して ai-tutor-service を呼ぶ。
// 他画面（home.ts/map.ts）と同じ VITE_API_URL に統一。未設定時は同一オリジンの /api。
// 開発では vite が /api を localhost:8000 にプロキシするため、未設定でも動く。
const API_BASE = import.meta.env.VITE_API_URL ?? "";
const AI_TUTOR_BASE = import.meta.env.VITE_AI_TUTOR_URL ?? API_BASE;

export type ConversationState = "questioning" | "ready_to_finish";

export interface StartSessionResponse {
  session_id: string;
  message: string;
}

export interface SendMessageResponse {
  message: string;
  state: ConversationState;
}

export interface FinishResponse {
  session_id: string;
  score: number;
  summary: string;
  strengths: string[];
  weaknesses: string[];
  xp: number;
  // 自前バックエンド(chat.py)がキャラへ実際に付与した経験値情報。
  // ai-tutor を直接叩いた場合や付与0のときは付かないので任意。
  awarded_xp_minutes?: number;
  character_level?: number;
  leveled_up?: boolean;
  evolution_stage?: number;
}

async function post<T>(path: string, token: string | null, body?: unknown): Promise<T> {
  const res = await fetch(`${AI_TUTOR_BASE}${path}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(`${res.status} ${res.statusText}: ${detail}`);
  }
  return (await res.json()) as T;
}

// 配布された URL からアクセストークンを取り出す。
// ハッシュルーティングのため #/chat?token=... と ?token=...#/chat の両方に対応。
// 通常はログイン(auth.ts)で得たトークンを使うが、?token= 付き配布URLにも後方互換で対応する。
export function getTokenFromUrl(): string | null {
  const hashQuery = window.location.hash.split("?")[1] ?? "";
  const fromHash = new URLSearchParams(hashQuery).get("token");
  const fromSearch = new URLSearchParams(window.location.search).get("token");
  return fromHash ?? fromSearch;
}

// 本番では配布トークン (getTokenFromUrl) を使う。
// ここでは local 専用のデモ用トークン払い出しを叩く (APP_ENV=local のみ有効)。
export async function fetchDevToken(userId = "demo-student"): Promise<string> {
  const data = await post<{ token: string }>('/api/chat/dev/token', null, { user_id: userId });
  return data.token;
}

// 進化前=tsundere / 進化後=onee。キャラの進化段階から決めた口調。
// ai-tutor-service 側(app/services/persona.py)の定数と一致させる。
export type Persona = "tsundere" | "onee";

// 進化段階(evolution_stage)から口調を決める。進化前(0)はツンデレ、進化後(>=1)はお姉さん。
export function personaForStage(stage: number): Persona {
  return stage >= 1 ? "onee" : "tsundere";
}

export function startSession(token: string, persona?: Persona) {
  return post<StartSessionResponse>('/api/chat/sessions', token, { persona });
}

export function sendMessage(token: string, sessionId: string, message: string) {
  return post<SendMessageResponse>(`/api/chat/sessions/${sessionId}/messages`, token, { message });
}

export function finishSession(token: string, sessionId: string) {
  return post<FinishResponse>(`/api/chat/sessions/${sessionId}/finish`, token);
}
