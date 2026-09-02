// AI Tutor Service クライアント。
// 本番は VITE_AI_TUTOR_URL に AI Tutor の URL を渡す。未設定時は localhost:8000。
const AI_TUTOR_BASE = import.meta.env.VITE_AI_TUTOR_URL ?? "http://localhost:8000";

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

// 本番では既存 Backend の /login が発行する JWT を使う。
// ここでは local 専用のデモ用トークン払い出しを叩く。
export async function fetchDevToken(userId = "demo-student"): Promise<string> {
  const data = await post<{ token: string }>("/dev/token", null, { user_id: userId });
  return data.token;
}

export function startSession(token: string) {
  return post<StartSessionResponse>("/sessions", token);
}

export function sendMessage(token: string, sessionId: string, message: string) {
  return post<SendMessageResponse>(`/sessions/${sessionId}/messages`, token, { message });
}

export function finishSession(token: string, sessionId: string) {
  return post<FinishResponse>(`/sessions/${sessionId}/finish`, token);
}
