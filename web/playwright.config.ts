import { defineConfig, devices } from "@playwright/test";
import path from "path";

const apiDir = path.join(__dirname, "..", "api");

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  timeout: 120_000,
  expect: { timeout: 15_000 },
  use: {
    baseURL: "http://127.0.0.1:3000",
    trace: "on-first-retry",
  },
  webServer: [
    {
      command:
        "INTERVIEWOS_AUTH_BYPASS=1 DATABASE_URL=sqlite+pysqlite:///./playwright.db PYTHONPATH=src python3 -m uvicorn interviewos.http.app:app --host 127.0.0.1 --port 8000",
      cwd: apiDir,
      url: "http://127.0.0.1:8000/health",
      reuseExistingServer: !process.env.CI,
      timeout: 120_000,
    },
    {
      command: "npm run dev -- --port 3000 --hostname 127.0.0.1",
      url: "http://127.0.0.1:3000",
      reuseExistingServer: !process.env.CI,
      timeout: 120_000,
    },
  ],
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
});
