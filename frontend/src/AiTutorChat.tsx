import { useEffect, useRef, useState } from "react";
import {
  fetchDevToken,
  finishSession,
  getTokenFromUrl,
  sendMessage,
  startSession,
  type ConversationState,
  type FinishResponse,
} from "./aiTutor";
import { clearStoredToken, getStoredToken, login } from "./auth";

interface ChatMessage {
  role: "assistant" | "user";
  content: string;
}

export default function AiTutorChat() {
  // トークンの取得順: ログイン保存 → 配布URL(?token=)。どちらも無ければログインフォーム。
  const [token, setToken] = useState<string | null>(() => getStoredToken() ?? getTokenFromUrl());
  // token が無いときだけ、local(APP_ENV=local)向けに dev トークン自動取得を試す。
  const [authChecking, setAuthChecking] = useState(() => (getStoredToken() ?? getTokenFromUrl()) === null);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [state, setState] = useState<ConversationState | null>(null);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<FinishResponse | null>(null);
  const logRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    logRef.current?.scrollTo({ top: logRef.current.scrollHeight });
  }, [messages, result]);

  // token 未取得のときだけ dev トークン取得を試す。
  // local では成功してログイン不要、本番では /dev/token が 404 なので失敗しフォームを出す。
  useEffect(() => {
    if (token !== null) {
      setAuthChecking(false);
      return;
    }
    let cancelled = false;
    setAuthChecking(true);
    fetchDevToken()
      .then((t) => {
        if (!cancelled) setToken(t);
      })
      .catch(() => {})
      .finally(() => {
        if (!cancelled) setAuthChecking(false);
      });
    return () => {
      cancelled = true;
    };
  }, [token]);

  const finished = result !== null;

  function handleLogout() {
    clearStoredToken();
    setToken(null);
    setSessionId(null);
    setMessages([]);
    setState(null);
    setResult(null);
    setError(null);
  }

  async function handleStart() {
    if (!token) return;
    setError(null);
    setLoading(true);
    try {
      const s = await startSession(token);
      setSessionId(s.session_id);
      setMessages([{ role: "assistant", content: s.message }]);
      setState("questioning");
      setResult(null);
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }

  async function handleSend() {
    const text = input.trim();
    if (!text || !token || !sessionId || loading) return;
    setError(null);
    setInput("");
    setMessages((m) => [...m, { role: "user", content: text }]);
    setLoading(true);
    try {
      const res = await sendMessage(token, sessionId, text);
      setMessages((m) => [...m, { role: "assistant", content: res.message }]);
      setState(res.state);
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }

  async function handleFinish() {
    if (!token || !sessionId || loading) return;
    setError(null);
    setLoading(true);
    try {
      setResult(await finishSession(token, sessionId));
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }

  if (authChecking) {
    return (
      <section style={styles.wrap}>
        <p style={styles.hint}>確認中…</p>
      </section>
    );
  }

  if (!token) {
    return (
      <section style={styles.wrap}>
        <h2 style={{ margin: "0 0 4px" }}>ログイン</h2>
        <p style={styles.hint}>配布された ID とパスワードでログインしてください。</p>
        <LoginForm onLogin={setToken} />
      </section>
    );
  }

  return (
    <section style={styles.wrap}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
        <h2 style={{ margin: "0 0 4px" }}>AIチューターと話す</h2>
        <button style={styles.link} onClick={handleLogout}>ログアウト</button>
      </div>
      <p style={styles.hint}>
        今日勉強したことを話してみよう。AIが興味を持って聞いて、一緒に理解を深めてくれます。
      </p>

      {!sessionId ? (
        <button style={styles.primary} onClick={handleStart} disabled={loading}>
          {loading ? "接続中…" : "会話を始める"}
        </button>
      ) : (
        <>
          <div ref={logRef} style={styles.log}>
            {messages.map((m, i) => (
              <div key={i} style={m.role === "user" ? styles.userRow : styles.aiRow}>
                <span style={m.role === "user" ? styles.userBubble : styles.aiBubble}>
                  {m.content}
                </span>
              </div>
            ))}
            {loading && <div style={styles.aiRow}><span style={styles.aiBubble}>…</span></div>}
          </div>

          {result ? (
            <div style={styles.report}>
              <h3 style={{ margin: "0 0 8px" }}>評価レポート</h3>
              <p style={{ margin: "4px 0" }}>
                理解度スコア: <b>{result.score}</b> / 100&emsp;&emsp;獲得XP: <b>{result.xp}</b>
              </p>
              <p style={{ margin: "4px 0" }}>{result.summary}</p>
              <p style={{ margin: "8px 0 2px" }}><b>強み</b></p>
              <ul style={{ margin: 0 }}>{result.strengths.map((s, i) => <li key={i}>{s}</li>)}</ul>
              <p style={{ margin: "8px 0 2px" }}><b>弱点</b></p>
              <ul style={{ margin: 0 }}>{result.weaknesses.map((w, i) => <li key={i}>{w}</li>)}</ul>
              <button style={{ ...styles.primary, marginTop: 12 }} onClick={handleStart}>
                もう一度
              </button>
            </div>
          ) : (
            <div style={styles.inputRow}>
              <textarea
                style={styles.input}
                value={input}
                rows={3}
                placeholder="話したいことを入力…（Enterで改行 / ⌘・Ctrl+Enterで送信）"
                disabled={loading || finished}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => {
                  // IME変換確定のEnterや通常のEnterでは送信しない。
                  if (
                    e.key === "Enter" &&
                    (e.metaKey || e.ctrlKey) &&
                    !e.nativeEvent.isComposing
                  ) {
                    e.preventDefault();
                    handleSend();
                  }
                }}
              />
              <div style={styles.buttonCol}>
                <button style={styles.primary} onClick={handleSend} disabled={loading || !input.trim()}>
                  送信
                </button>
                <button
                  style={styles.finish}
                  onClick={handleFinish}
                  disabled={loading}
                  title={state === "ready_to_finish" ? "十分に話せました" : undefined}
                >
                  終了して評価
                </button>
              </div>
            </div>
          )}
          {state === "ready_to_finish" && !result && (
            <p style={styles.readyHint}>十分に確認できました。「終了して評価」を押せます。</p>
          )}
        </>
      )}

      {error && <p style={styles.error}>{error}</p>}
    </section>
  );
}

function LoginForm({ onLogin }: { onLogin: (token: string) => void }) {
  const [userId, setUserId] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!userId.trim() || !password || loading) return;
    setError(null);
    setLoading(true);
    try {
      onLogin(await login(userId.trim(), password));
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} style={styles.loginForm}>
      <input
        style={styles.input}
        value={userId}
        placeholder="ID"
        autoComplete="username"
        onChange={(e) => setUserId(e.target.value)}
      />
      <input
        style={styles.input}
        type="password"
        value={password}
        placeholder="パスワード"
        autoComplete="current-password"
        onChange={(e) => setPassword(e.target.value)}
      />
      <button style={styles.primary} type="submit" disabled={loading || !userId.trim() || !password}>
        {loading ? "ログイン中…" : "ログイン"}
      </button>
      {error && <p style={styles.error}>{error}</p>}
    </form>
  );
}

const styles: Record<string, React.CSSProperties> = {
  wrap: { maxWidth: 640, margin: "0 auto", fontFamily: "sans-serif" },
  hint: { color: "#555", fontSize: 14, margin: "0 0 12px" },
  log: {
    border: "1px solid #ddd", borderRadius: 8, padding: 12, height: 360,
    overflowY: "auto", background: "#fafafa",
  },
  aiRow: { display: "flex", justifyContent: "flex-start", margin: "6px 0" },
  userRow: { display: "flex", justifyContent: "flex-end", margin: "6px 0" },
  aiBubble: {
    background: "#eef2ff", color: "#1e293b", padding: "8px 12px",
    borderRadius: 12, maxWidth: "80%", whiteSpace: "pre-wrap",
  },
  userBubble: {
    background: "#2563eb", color: "#fff", padding: "8px 12px",
    borderRadius: 12, maxWidth: "80%", whiteSpace: "pre-wrap",
  },
  inputRow: { display: "flex", gap: 8, marginTop: 12, alignItems: "stretch" },
  input: {
    flex: 1, padding: "8px 10px", borderRadius: 8, border: "1px solid #ccc",
    fontFamily: "inherit", fontSize: 14, resize: "vertical",
  },
  buttonCol: { display: "flex", flexDirection: "column", gap: 8 },
  primary: {
    padding: "8px 16px", borderRadius: 8, border: "none",
    background: "#2563eb", color: "#fff", cursor: "pointer",
  },
  finish: {
    padding: "8px 16px", borderRadius: 8, border: "1px solid #2563eb",
    background: "#fff", color: "#2563eb", cursor: "pointer",
  },
  readyHint: { color: "#059669", fontSize: 13, margin: "8px 0 0" },
  loginForm: { display: "flex", flexDirection: "column", gap: 8, maxWidth: 320 },
  link: {
    border: "none", background: "none", color: "#2563eb", cursor: "pointer",
    fontSize: 13, padding: 0,
  },
  report: { marginTop: 12, padding: 16, border: "1px solid #ddd", borderRadius: 8, background: "#fff" },
  error: { color: "#dc2626", fontSize: 13, marginTop: 8, whiteSpace: "pre-wrap" },
};
