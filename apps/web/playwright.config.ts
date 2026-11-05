import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  forbidOnly: Boolean(process.env.CI),
  retries: process.env.CI ? 1 : 0,
  workers: 1,
  reporter: process.env.CI ? [["line"], ["html", { open: "never" }]] : "line",
  use: {
    baseURL: "http://127.0.0.1:3100",
    screenshot: "only-on-failure",
    trace: "retain-on-failure",
    video: "retain-on-failure",
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
  webServer: [
    {
      command: "node e2e/support/mock-api.mjs",
      port: 4100,
      reuseExistingServer: !process.env.CI,
      timeout: 30_000,
    },
    {
      command: "npm run build && npm run start",
      env: {
        API_INTERNAL_BASE_URL: "http://127.0.0.1:4100",
        HOSTNAME: "127.0.0.1",
        NEXT_PUBLIC_API_BASE_URL: "http://127.0.0.1:4100",
        PORT: "3100",
      },
      port: 3100,
      reuseExistingServer: !process.env.CI,
      timeout: 180_000,
    },
  ],
});
