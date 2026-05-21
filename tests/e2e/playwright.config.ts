import { defineConfig, devices } from "@playwright/test";
import path from "path";

/** Ejecutar desde tests/e2e (npm run test:e2e). */
const E2E_ROOT = process.cwd();
const REPO_ROOT = path.resolve(E2E_ROOT, "..", "..");

const PORT = Number(process.env.ELIA_E2E_PORT || 8765);
const BASE_URL = `http://127.0.0.1:${PORT}`;

const pythonExe =
  process.platform === "win32"
    ? path.join(REPO_ROOT, ".venv", "Scripts", "python.exe")
    : path.join(REPO_ROOT, ".venv", "bin", "python");

const serveScript = path.join(E2E_ROOT, "scripts", "e2e_serve.py");

export default defineConfig({
  testDir: "./specs",
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  workers: 1,
  reporter: [["list"], ["html", { open: "never", outputFolder: "report" }]],
  timeout: 60_000,
  expect: { timeout: 10_000 },
  use: {
    baseURL: BASE_URL,
    trace: "on-first-retry",
    screenshot: "only-on-failure",
    video: "retain-on-failure",
    locale: "es-MX",
  },
  globalSetup: "./global-setup.ts",
  webServer: {
    command: `"${pythonExe}" "${serveScript}"`,
    url: BASE_URL,
    reuseExistingServer: false,
    timeout: 120_000,
    cwd: REPO_ROOT,
    env: {
      ELIA_E2E_PORT: String(PORT),
    },
  },
  projects: [
    {
      name: "license-flow",
      testMatch: /license\.spec\.ts/,
      use: { ...devices["Desktop Chrome"] },
    },
    {
      name: "app",
      testMatch: /^(?!.*license\.spec).*\.spec\.ts/,
      dependencies: ["license-flow"],
      use: { ...devices["Desktop Chrome"] },
    },
  ],
});
