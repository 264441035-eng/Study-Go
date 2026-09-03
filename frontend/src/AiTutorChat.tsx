import { useEffect, useRef, useState } from "react";
import "./chat.css";
import {
  fetchDevToken,
  finishSession,
  getTokenFromUrl,
  personaForStage,
  sendMessage,
  startSession,
  type ConversationState,
  type FinishResponse,
} from "./aiTutor";
import { clearStoredToken, getStoredToken, login } from "./auth";
import { appearanceForStage } from "../character";

// 他画面（home.ts/map.ts）と同じ VITE_API_URL に統一。未設定時は同一オリジンの /api。
const API_BASE = import.meta.env.VITE_API_URL ?? "";

interface ChatMessage {
  role: "assistant" | "user";
  content: string;
}

// ホームに戻る（MPA なので index.html へ遷移）。
function goHome() {
  window.location.href = "index.html";
}

// チャット画面に表示する小さなキャラクター。
// 進化前(PNG)は CSS で「ぴょこぴょこ」動かし、進化後(GIF)はそのまま再生する。
// celebrateKey が変わるたびに「激しく喜ぶ」アニメーションを一度だけ再生する
// （生徒が回答して返事が返ってきたときなど）。stage は親が保持する。
function ChatCharacter({
  stage,
  celebrateKey,
}: {
  stage: number;
  celebrateKey: number;
}) {
  const [celebrating, setCelebrating] = useState(false);

  useEffect(() => {
    // 初期表示(0)では動かさない。値が変わったときだけ短く喜ばせる。
    if (celebrateKey === 0) return;
    setCelebrating(true);
    const timer = window.setTimeout(() => setCelebrating(false), 900);
    return () => window.clearTimeout(timer);
  }, [celebrateKey]);

  const appearance = appearanceForStage(stage);
  // 喜んでいる間は celebration を優先し、それ以外は進化前だけ「ぴょこぴょこ」。
  const motionClass = celebrating
    ? " is-celebrating"
    : appearance.bounce
      ? " is-bouncing"
      : "";
  return (
    <div className="chat-character-wrap">
      <img
        className={`chat-character${motionClass}`}
        src={appearance.src}
        alt="あなたのキャラクター"
      />
    </div>
  );
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
  // 値が変わるとチャット画面のキャラの進化段階を取り直す。
  const [characterRefreshKey, setCharacterRefreshKey] = useState(0);
  // キャラの進化段階。口調(persona)の決定とアニメーションに使う。
  const [stage, setStage] = useState(0);
  // 値が変わるたびにキャラが「激しく喜ぶ」。生徒の回答に反応させるため。
  const [celebrateKey, setCelebrateKey] = useState(0);
  const logRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    logRef.current?.scrollTo({ top: logRef.current.scrollHeight });
  }, [messages, result]);

  // キャラの進化段階を取得する。characterRefreshKey が変わると取り直す
  // （チャット完了で経験値が増えて進化した後など）。
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const initRes = await fetch(`${API_BASE}/api/characters/initialize`, {
          method: "POST",
        });
        if (!initRes.ok) return;
        const id = await initRes.json();
        const res = await fetch(`${API_BASE}/api/characters/${id}`);
        if (!res.ok) return;
        const data = await res.json();
        if (!cancelled && typeof data.evolution_stage === "number") {
          setStage(data.evolution_stage);
        }
      } catch {
        // キャラが取れなくてもチャットは使えるので、静かに諦める（進化前の絵のまま）。
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [characterRefreshKey]);

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
      // 進化段階に応じた口調（進化前=ツンデレ / 進化後=お姉さん）で会話させる。
      const s = await startSession(token, personaForStage(stage));
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
      // 生徒の回答にAIが返事したので、キャラを激しく喜ばせる。
      setCelebrateKey((k) => k + 1);
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
      // 経験値が増えてキャラが進化しているかもしれないので取り直す。
      setCharacterRefreshKey((k) => k + 1);
      // 評価が出たお祝いに、キャラを激しく喜ばせる。
      setCelebrateKey((k) => k + 1);
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }

  if (authChecking) {
    return (
      <div className="chat-page">
        <section className="chat-panel">
          <p className="chat-hint">確認中…</p>
        </section>
      </div>
    );
  }

  if (!token) {
    return (
      <div className="chat-page">
        <header className="chat-header">
          <button className="back-button" type="button" onClick={goHome}>← ホームに戻る</button>
        </header>
        <section className="chat-panel">
          <h1>AIチューター</h1>
          <p className="chat-hint">配布された ID とパスワードでログインしてください。</p>
          <LoginForm onLogin={setToken} />
        </section>
      </div>
    );
  }

  return (
    <div className="chat-page">
      <header className="chat-header">
        <button className="back-button" type="button" onClick={goHome}>← ホームに戻る</button>
        <button className="logout-link" type="button" onClick={handleLogout}>ログアウト</button>
      </header>

      <section className="chat-panel">
        <ChatCharacter stage={stage} celebrateKey={celebrateKey} />
        <h1>AIチューター</h1>
        <p className="chat-hint">
          今日勉強したことを話してみよう。AIが興味を持って聞いて、一緒に理解を深めてくれます。
        </p>

        {!sessionId ? (
          <button className="start-button" type="button" onClick={handleStart} disabled={loading}>
            {loading ? "接続中…" : "会話を始める"}
          </button>
        ) : (
          <>
            <div ref={logRef} className="chat-log" aria-live="polite">
              {messages.map((m, i) => (
                <div key={i} className={`row ${m.role === "user" ? "user-row" : "ai-row"}`}>
                  <span className={`bubble ${m.role === "user" ? "user-bubble" : "ai-bubble"}`}>
                    {m.content}
                  </span>
                </div>
              ))}
              {loading && (
                <div className="row ai-row">
                  <span className="bubble ai-bubble">…</span>
                </div>
              )}
            </div>

            {result ? (
              <div className="report">
                <h3>評価レポート</h3>
                {result.awarded_xp_minutes ? (
                  <p className="xp-gain" role="status">
                    🎉 経験値を <b>{result.awarded_xp_minutes}</b> 獲得！
                    {result.leveled_up && result.character_level
                      ? ` レベルが ${result.character_level} に上がったよ！`
                      : " ホームで育ち具合をチェックしてみよう。"}
                  </p>
                ) : null}
                <p style={{ margin: "4px 0" }}>
                  理解度スコア: <b>{result.score}</b> / 100
                </p>
                <p style={{ margin: "4px 0" }}>{result.summary}</p>
                <p style={{ margin: "8px 0 2px" }}><b>👍 いいところ</b></p>
                <ul>{result.strengths.map((s, i) => <li key={i}>{s}</li>)}</ul>
                <p style={{ margin: "8px 0 2px" }}><b>💪 もう一歩</b></p>
                <ul>{result.weaknesses.map((w, i) => <li key={i}>{w}</li>)}</ul>
                <button className="start-button" type="button" onClick={handleStart} style={{ marginTop: 12 }}>
                  もう一度
                </button>
              </div>
            ) : (
              <div className="input-wrap">
                <textarea
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
                <div className="action-stack">
                  <button className="send-button" type="button" onClick={handleSend} disabled={loading || !input.trim()}>
                    送信
                  </button>
                  <button
                    className="finish-button"
                    type="button"
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
              <p className="ready-hint">十分に確認できました。「終了して評価」を押せます。</p>
            )}
          </>
        )}

        {error && <p className="chat-error">{error}</p>}
      </section>
    </div>
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
    <form onSubmit={handleSubmit} className="login-form">
      <input
        value={userId}
        placeholder="ID"
        autoComplete="username"
        onChange={(e) => setUserId(e.target.value)}
      />
      <input
        type="password"
        value={password}
        placeholder="パスワード"
        autoComplete="current-password"
        onChange={(e) => setPassword(e.target.value)}
      />
      <button className="send-button" type="submit" disabled={loading || !userId.trim() || !password}>
        {loading ? "ログイン中…" : "ログイン"}
      </button>
      {error && <p className="chat-error">{error}</p>}
    </form>
  );
}
