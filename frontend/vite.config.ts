import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],

  server: {
    host: true,
    port: 5173,
  },

  build: {
    rollupOptions: {
      input: {
        main: "index.html",
        study: "study.html",
        map: "map.html",
        task: "task.html",
        training: "training.html",
      },
    },
  },
});