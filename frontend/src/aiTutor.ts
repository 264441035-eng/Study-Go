// AI Tutor Service クライアント。
// Frontend は自前バックエンドを経由して ai-tutor-service を呼ぶ。
const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";
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

export function startSession(token: string) {
  return post<StartSessionResponse>('/api/chat/sessions', token);
}

export function sendMessage(token: string, sessionId: string, message: string) {
  return post<SendMessageResponse>(`/api/chat/sessions/${sessionId}/messages`, token, { message });
}

export function finishSession(token: string, sessionId: string) {
  return post<FinishResponse>(`/api/chat/sessions/${sessionId}/finish`, token);
}
