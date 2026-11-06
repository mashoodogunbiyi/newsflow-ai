import { spawn } from "node:child_process";
import { mkdir } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

import { chromium } from "@playwright/test";

const scriptDirectory = dirname(fileURLToPath(import.meta.url));
const webDirectory = resolve(scriptDirectory, "..");
const repositoryRoot = resolve(webDirectory, "..", "..");
const screenshotDirectory = resolve(repositoryRoot, "docs", "screenshots");
const applicationUrl = "http://localhost:3100";
const mockApiUrl = "http://127.0.0.1:4100";
const children = [];

function start(command, args, options = {}) {
  const child = spawn(command, args, {
    cwd: webDirectory,
    env: { ...process.env, ...options.env },
    stdio: "inherit",
  });
  children.push(child);
  return child;
}

async function waitFor(url, process, label) {
  for (let attempt = 0; attempt < 120; attempt += 1) {
    if (process.exitCode !== null) {
      throw new Error(`${label} stopped before it became available.`);
    }
    try {
      const response = await fetch(url);
      if (response.ok) return;
    } catch {
      // The service is still starting.
    }
    await new Promise((resolveWait) => setTimeout(resolveWait, 500));
  }
  throw new Error(`${label} did not become available in time.`);
}

async function stopChildren() {
  await Promise.all(
    children.map(
      (child) =>
        new Promise((resolveStop) => {
          if (child.exitCode !== null) {
            resolveStop();
            return;
          }
          child.once("exit", resolveStop);
          child.kill("SIGTERM");
          setTimeout(() => {
            if (child.exitCode === null) child.kill("SIGKILL");
          }, 5_000).unref();
        }),
    ),
  );
}

async function capture(page, filename) {
  await page.screenshot({
    path: resolve(screenshotDirectory, filename),
    fullPage: false,
  });
}

async function main() {
  await mkdir(screenshotDirectory, { recursive: true });

  const mockApi = start(process.execPath, ["e2e/support/mock-api.mjs"]);
  const frontend = start("npm", ["run", "dev"], {
    env: {
      API_INTERNAL_BASE_URL: mockApiUrl,
      HOSTNAME: "127.0.0.1",
      NEXT_PUBLIC_API_BASE_URL: mockApiUrl,
      PORT: "3100",
    },
  });

  await waitFor(`${mockApiUrl}/health`, mockApi, "Synthetic API");
  await waitFor(applicationUrl, frontend, "Next.js frontend");

  const browser = await chromium.launch();
  try {
    const context = await browser.newContext({
      colorScheme: "light",
      reducedMotion: "reduce",
      viewport: { width: 1440, height: 960 },
    });
    const page = await context.newPage();

    await fetch(`${mockApiUrl}/__test/reset`, { method: "POST" });
    await page.goto(applicationUrl);
    await page.getByRole("heading", { name: /Turn careful reporting/i }).waitFor();
    await capture(page, "homepage.png");

    await page.goto(`${applicationUrl}/login`);
    await page.getByLabel("Email address").fill("owner@example.com");
    await page.getByLabel("Password", { exact: true }).fill("TestPassword123!");
    await page.getByRole("button", { name: "Sign in" }).click();
    await page.getByRole("heading", { name: "From trusted link to thoughtful post." }).waitFor();
    await capture(page, "article-dashboard.png");

    await page.getByRole("link", { name: "Select article" }).click();
    await page.getByRole("button", { name: "Generate LinkedIn draft" }).click();
    await page.getByText("Your private draft has been generated.").waitFor();
    await page
      .getByRole("textbox", { name: "LinkedIn draft text" })
      .fill("A human-reviewed synthetic LinkedIn draft with preserved attribution.");
    await page.getByRole("button", { name: "Generate image" }).click();
    await page.getByText("Your private illustration is ready for review.").waitFor();
    await page.getByRole("textbox", { name: "LinkedIn draft text" }).scrollIntoViewIfNeeded();
    await capture(page, "generation-workspace.png");

    await page.getByRole("button", { name: "Save to library" }).click();
    await page.getByRole("heading", { name: "Continue editing your saved draft." }).waitFor();
    await page.goto(`${applicationUrl}/library`);
    await page.getByRole("heading", { name: "Your saved work, ready to continue." }).waitFor();
    await capture(page, "content-library.png");

    await context.close();
  } finally {
    await browser.close();
  }

  console.log(`Documentation screenshots written to ${screenshotDirectory}`);
}

try {
  await main();
} finally {
  await stopChildren();
}
