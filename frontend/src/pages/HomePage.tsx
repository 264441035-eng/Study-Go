export default function HomePage() {
  return (
    <div style={{ maxWidth: 640, margin: "0 auto", textAlign: "center" }}>
      <h1>Study-Go</h1>
      <p style={{ color: "#555" }}>
        今日勉強したことを、AIチューターに話してみよう。
      </p>
      <a href="#/chat" style={styles.cta}>
        AIチューターと話す
      </a>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  cta: {
    display: "inline-block",
    marginTop: 16,
    padding: "12px 24px",
    borderRadius: 10,
    background: "#2563eb",
    color: "#fff",
    textDecoration: "none",
    fontWeight: 600,
  },
};
