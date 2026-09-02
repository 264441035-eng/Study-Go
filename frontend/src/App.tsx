import { useEffect, useState } from "react";
import ChatPage from "./pages/ChatPage";
import Home from "./home";
import Study from "./study";

// --------------------------------
// ハッシュルーティング
//
// #/       → ホーム
// #/chat   → チャット
// #/study  → 勉強
// --------------------------------
function useHashRoute() {
  const [hash, setHash] = useState(() => window.location.hash);

  useEffect(() => {
    const onChange = () => {
      setHash(window.location.hash);
    };

    window.addEventListener("hashchange", onChange);

    return () => {
      window.removeEventListener("hashchange", onChange);
    };
  }, []);

  return hash;
}

export default function App() {
  const hash = useHashRoute();
  const path = hash.split("?")[0];

  // チャット
  if (path === "#/chat") {
    return (
      <main
        style={{
          fontFamily: "sans-serif",
          padding: 32,
        }}
      >
        <ChatPage />
      </main>
    );
  }

  
  // 勉強
  if (path === "#/study") {
    return (
      <main
        style={{
          fontFamily: "sans-serif",
          padding: 32,
        }}
      >
        <Study />
      </main>
    );
  }

  // ホーム
  return (
    <main
      style={{
        fontFamily: "sans-serif",
        padding: 32,
      }}
    >
      <Home />
    </main>
  );
}