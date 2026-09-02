import { useEffect, useState } from "react";
import ChatPage from "./pages/ChatPage";
import HomePage from "./pages/HomePage";

// 依存を増やさない最小のハッシュルーティング (#/chat でチャットページ)。
function useHashRoute() {
  const [hash, setHash] = useState(() => window.location.hash);
  useEffect(() => {
    const onChange = () => setHash(window.location.hash);
    window.addEventListener("hashchange", onChange);
    return () => window.removeEventListener("hashchange", onChange);
  }, []);
  return hash;
}

export default function App() {
  const hash = useHashRoute();
  const path = hash.split("?")[0];
  const page = path === "#/chat" ? <ChatPage /> : <HomePage />;
  return <main style={{ fontFamily: "sans-serif", padding: 32 }}>{page}</main>;
}
