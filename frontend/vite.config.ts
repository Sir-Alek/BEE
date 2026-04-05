import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  // SPA: assets paths should work when served from FastAPI local root.
  // Vite will emit `/assets/...` by default with `base: '/'`.
  base: "/",
  server: {
    host: "127.0.0.1",
  },
});

