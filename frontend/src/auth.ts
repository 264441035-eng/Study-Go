// ログイン認証クライアント。
// backend の /api/auth/login で JWT を取得し、localStorage に保持する。
// このトークンを AI Tutor 呼び出しの Authorization に使う（aiTutor.ts）。
const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";
const TOKEN_KEY = "ai_tutor_token";

export interface LoginResponse {
  token: string;
  user_id: string;
}

export function getStoredToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function setStoredToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearStoredToken(): void {
  localStorage.removeItem(TOKEN_KEY);
}

// ログインして JWT を取得・保存する。失敗時は例外。
export async function login(userId: string, password: string): Promise<string> {
  const res = await fetch(`${API_BASE}/api/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ user_id: userId, password }),
  });
  if (res.status === 401) {
    throw new Error("IDまたはパスワードが正しくありません。");
  }
  if (!res.ok) {
    throw new Error(`ログインに失敗しました (${res.status})`);
  }
  const data = (await res.json()) as LoginResponse;
  setStoredToken(data.token);
  return data.token;
}
