import { copyFileSync, existsSync, mkdirSync } from "fs";
import path from "path";
import { fileURLToPath } from "url";
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

function copySplashLogo() {
  return {
    name: "elia-copy-splash-logo",
    buildStart() {
      const src = path.resolve(__dirname, "../resources/logo_elia_full.png");
      const destDir = path.resolve(__dirname, "public");
      const dest = path.join(destDir, "logo_elia_full.png");
      if (!existsSync(src)) return;
      mkdirSync(destDir, { recursive: true });
      copyFileSync(src, dest);
    },
  };
}

export default defineConfig({
  plugins: [react(), copySplashLogo()],
  // SPA: assets paths should work when served from FastAPI local root.
  // Vite will emit `/assets/...` by default with `base: '/'`.
  base: "/",
  server: {
    host: "127.0.0.1",
  },
});
