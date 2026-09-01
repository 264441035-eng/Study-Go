import { useEffect, useState } from "react";

// 本番では VITE_API_URL に ALB の URL を渡す。未設定時は同一オリジンの /api を叩く。
const API_BASE = import.meta.env.VITE_API_URL ?? "";

export default function App() {
  const [message, setMessage] = useState("loading...");

  useEffect(() => {
    fetch(`${API_BASE}/api/hello`)
      .then((r) => r.json())
      .then((d) => setMessage(d.message))
      .catch((e) => setMessage(`error: ${String(e)}`));
  }, []);

  return (
    <main style={{ fontFamily: "sans-serif", padding: 32 }}>
      <h1>Study-Go</h1>
      <p>Backend says: {message}</p>
    </main>
  );
}
