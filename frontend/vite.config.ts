import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],

  server: {
    host: true,
    port: 5173,
    // 本番はnginxが同一オリジンで/apiをバックエンドにプロキシしているので、
    // 開発サーバーでも同じ挙動に揃える（VITE_API_URL未設定でも動くように）。
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },

  build: {
    rollupOptions: {
      input: {
        main: "index.html",
        chat: "chat.html",
        study: "study.html",
        map: "map.html",
        task: "task.html",
        training: "training.html",
      },
    },
  },
});