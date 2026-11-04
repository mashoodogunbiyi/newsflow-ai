import { readFile } from "node:fs/promises";
import { resolve } from "node:path";

import { expect, test, type Page } from "@playwright/test";

import { MOCK_API_URL, resetTestState, signIn } from "./helpers";

const ARTICLE_ID = "10000000-0000-4000-8000-000000000001";
const IMAGE_ID = "40000000-0000-4000-8000-000000000004";
const DASHBOARD_DOM_CONTENT_LOADED_TARGET_MS = 3_000;
const DASHBOARD_LOAD_TARGET_MS = 4_000;
const PRIVATE_IMAGE_TARGET_MS = 1_000;

type AxeViolation = {
  help: string;
  id: string;
  impact: string | null;
  nodes: Array<{ target: string[] }>;
};

type MockMetrics = {
  articleDetail: number;
  articleList: number;
  authenticationState: number;
  draftDetail: number;
  draftList: number;
  generation: number;
  imageContent: number;
  imageDownload: number;
};

async function runAxe(page: Page) {
  const axeSource = await readFile(
    resolve(process.cwd(), "node_modules/axe-core/axe.min.js"),
    "utf8",
  );
  await page.addScriptTag({ content: axeSource });
  return page.evaluate(async () => {
    const axe = (
      window as typeof window & {
        axe: {
          run: (context: Document, options: object) => Promise<{ violations: AxeViolation[] }>;
        };
      }
    ).axe;
    const result = await axe.run(document, {
      runOnly: {
        type: "tag",
        values: ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"],
      },
    });
    return result.violations;
  });
}

function expectNoAxeViolations(violations: AxeViolation[]) {
  expect(
    violations.map((violation) => ({
      help: violation.help,
      id: violation.id,
      impact: violation.impact,
      targets: violation.nodes.flatMap((node) => node.target),
    })),
  ).toEqual([]);
}

test.beforeEach(async ({ request }) => resetTestState(request));

test("keeps dashboard navigation within performance and request-count budgets", async ({
  page,
  request,
}) => {
  await signIn(page);
  const resetMetrics = await request.post(`${MOCK_API_URL}/__test/metrics/reset`);
  expect(resetMetrics.ok()).toBeTruthy();

  await page.goto("/dashboard");
  await expect(page.getByRole("heading", { name: "Find a story worth sharing." })).toBeVisible();
  const navigation = await page.evaluate(() => {
    const entry = performance.getEntriesByType("navigation")[0] as PerformanceNavigationTiming;
    return {
      domContentLoadedMs: entry.domContentLoadedEventEnd - entry.startTime,
      loadMs: entry.loadEventEnd - entry.startTime,
      responseStartMs: entry.responseStart - entry.startTime,
    };
  });
  const metricsResponse = await request.get(`${MOCK_API_URL}/__test/metrics`);
  const metrics = (await metricsResponse.json()) as MockMetrics;

  console.log("NFA80_BROWSER_METRIC", JSON.stringify({ dashboard: navigation, requests: metrics }));
  expect(navigation.domContentLoadedMs).toBeLessThanOrEqual(DASHBOARD_DOM_CONTENT_LOADED_TARGET_MS);
  expect(navigation.loadMs).toBeLessThanOrEqual(DASHBOARD_LOAD_TARGET_MS);
  expect(metrics.articleList).toBe(1);
  expect(metrics.draftList).toBe(0);
});

for (const viewport of [
  { height: 812, label: "mobile", width: 375 },
  { height: 1024, label: "tablet", width: 768 },
  { height: 900, label: "desktop", width: 1440 },
]) {
  test(`passes browser accessibility and overflow checks at ${viewport.label} size`, async ({
    page,
  }) => {
    await page.setViewportSize({ height: viewport.height, width: viewport.width });
    await signIn(page);
    await expect(page.getByLabel("Search permitted topics")).toBeVisible();

    expectNoAxeViolations(await runAxe(page));
    const layout = await page.evaluate(() => ({
      clientWidth: document.documentElement.clientWidth,
      scrollWidth: document.documentElement.scrollWidth,
    }));
    expect(layout.scrollWidth).toBeLessThanOrEqual(layout.clientWidth + 1);

    const accessibilityTree = await page.locator("#workspace-content").ariaSnapshot();
    expect(accessibilityTree).toContain("Find a story worth sharing.");
    expect(accessibilityTree).toContain("Search permitted topics");

    await page.emulateMedia({ reducedMotion: "reduce" });
    const longestMotionMs = await page
      .getByRole("button", { name: "Find articles" })
      .evaluate((element) => {
        const style = getComputedStyle(element);
        const toMilliseconds = (value: string) => {
          const number = Number.parseFloat(value);
          return value.trim().endsWith("ms") ? number : number * 1_000;
        };
        return Math.max(
          ...style.animationDuration.split(",").map(toMilliseconds),
          ...style.transitionDuration.split(",").map(toMilliseconds),
        );
      });
    expect(longestMotionMs).toBeLessThanOrEqual(0.02);
  });
}

test("supports skip-link, focus visibility, and mobile navigation by keyboard", async ({
  page,
}) => {
  await signIn(page);
  await page.goto("/dashboard");
  await page.keyboard.press("Tab");
  const skipLink = page.getByRole("link", { name: "Skip to main content" });
  await expect(skipLink).toBeFocused();
  await expect(skipLink).toBeVisible();
  const focusStyle = await skipLink.evaluate((element) => {
    const style = getComputedStyle(element);
    return { outlineStyle: style.outlineStyle, outlineWidth: style.outlineWidth };
  });
  expect(focusStyle.outlineStyle).not.toBe("none");
  expect(Number.parseFloat(focusStyle.outlineWidth)).toBeGreaterThanOrEqual(2);
  await page.keyboard.press("Enter");
  await expect(page.locator("#workspace-content")).toBeFocused();

  await page.setViewportSize({ height: 812, width: 375 });
  const openNavigation = page.getByRole("button", { name: "Open navigation" });
  await openNavigation.focus();
  await page.keyboard.press("Enter");
  const mobileNavigation = page.getByRole("navigation", { name: "Mobile workspace" });
  await expect(mobileNavigation.getByRole("link", { name: "Dashboard" })).toBeFocused();
  await page.keyboard.press("Escape");
  await expect(page.getByRole("button", { name: "Open navigation" })).toBeFocused();
});

test("exposes accessible validation and authentication errors", async ({ page }) => {
  await page.goto("/login");
  await page.getByLabel("Email address").fill("not-an-email");
  await page.getByRole("button", { name: "Sign in" }).click();
  const email = page.getByLabel("Email address");
  await expect(email).toBeFocused();
  await expect(email).toHaveAttribute("aria-invalid", "true");
  await expect(page.getByText("Enter a valid email address.")).toBeVisible();
  expectNoAxeViolations(await runAxe(page));

  await email.fill("owner@example.com");
  await page.getByLabel("Password", { exact: true }).fill("WrongPassword123!");
  await page.getByRole("button", { name: "Sign in" }).click();
  const error = page.getByRole("alert").filter({ hasText: "Invalid email or password." });
  await expect(error).toHaveText("Invalid email or password.");
  await expect(error).toBeFocused();
});

test("preserves generation choices and announces a provider timeout", async ({ page, request }) => {
  await signIn(page);
  await page.goto(`/generate?articleId=${ARTICLE_ID}`);
  await page.getByLabel("Analytical", { exact: false }).check();
  await page.getByLabel("Short").check();
  const configured = await request.post(`${MOCK_API_URL}/__test/generation-timeout`);
  expect(configured.ok()).toBeTruthy();

  await page.getByRole("button", { name: "Generate LinkedIn draft" }).click();
  const alert = page.getByRole("alert").filter({ hasText: "The draft could not be generated." });
  await expect(alert).toContainText("The draft could not be generated.");
  await expect(alert).toContainText("The AI provider took too long to respond.");
  await expect(page.getByLabel("Analytical", { exact: false })).toBeChecked();
  await expect(page.getByLabel("Short")).toBeChecked();
  await expect(page.getByRole("button", { name: "Try again" })).toBeVisible();
});

test("delivers an authenticated private image within the browser guardrail", async ({ page }) => {
  await signIn(page);
  const image = await page.evaluate(async (imageId) => {
    const started = performance.now();
    const response = await fetch(`/api/images/${imageId}/content`, { credentials: "same-origin" });
    const body = await response.arrayBuffer();
    return {
      bytes: body.byteLength,
      cacheControl: response.headers.get("cache-control"),
      durationMs: performance.now() - started,
      status: response.status,
    };
  }, IMAGE_ID);

  console.log("NFA80_BROWSER_METRIC", JSON.stringify({ privateImage: image }));
  expect(image.status).toBe(200);
  expect(image.bytes).toBeGreaterThan(0);
  expect(image.cacheControl).toContain("no-store");
  expect(image.durationMs).toBeLessThanOrEqual(PRIVATE_IMAGE_TARGET_MS);
});
