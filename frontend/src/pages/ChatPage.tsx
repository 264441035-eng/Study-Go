import AiTutorChat from "../AiTutorChat";

export default function ChatPage() {
  return (
    <div style={{ maxWidth: 640, margin: "0 auto" }}>
      <a href="#/" style={{ color: "#2563eb", textDecoration: "none", fontSize: 14 }}>
        ← ホームに戻る
      </a>
      <div style={{ height: 12 }} />
      <AiTutorChat />
    </div>
  );
}
