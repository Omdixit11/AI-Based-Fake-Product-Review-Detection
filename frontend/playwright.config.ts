import { defineConfig, devices } from "@playwright/test";
import path from "path";

const pythonExe = path.resolve(__dirname, "../.venv/Scripts/python.exe");

export default defineConfig({
  testDir: "./e2e",
  timeout: 60_000,
  expect: {
    timeout: 10_000,
  },
  fullyParallel: false,
  workers: 1,
  retries: 0,
  reporter: [["list"]],
  use: {
    baseURL: "http://localhost:3000",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
  webServer: [
    {
      command: `"${pythonExe}" -m uvicorn app.main:app --host 127.0.0.1 --port 8000`,
      cwd: path.resolve(__dirname, "../backend"),
      url: "http://127.0.0.1:8000/api/health",
      reuseExistingServer: true,
      timeout: 60_000,
    },
    {
      command: "npm run start -- -p 3000",
      cwd: __dirname,
      url: "http://localhost:3000/analyze",
      reuseExistingServer: true,
      timeout: 60_000,
    },
  ],
});
