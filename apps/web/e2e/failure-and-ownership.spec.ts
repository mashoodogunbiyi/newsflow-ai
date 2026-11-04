import { expect, test } from "@playwright/test";

import { DRAFT_ID, MOCK_API_URL, resetTestState, signIn } from "./helpers";

test.beforeEach(async ({ request }) => resetTestState(request));

test("shows deterministic empty and provider-failure states", async ({ page, request }) => {
  await signIn(page);
  await page.goto("/dashboard?search=no-results");
  await expect(
    page.getByRole("heading", { name: "No matching articles were found." }),
  ).toBeVisible();

  await page.goto("/generate?articleId=10000000-0000-4000-8000-000000000001");
  const configured = await request.post(`${MOCK_API_URL}/__test/generation-failure`);
  expect(configured.ok()).toBeTruthy();
  await page.getByRole("button", { name: "Generate LinkedIn draft" }).click();
  await expect(
    page.getByText("Mocked provider is temporarily unavailable.", { exact: true }),
  ).toBeVisible();
  await expect(page.getByRole("button", { name: "Try again" })).toBeVisible();
});

test("does not disclose another user's saved draft", async ({ page, request }) => {
  const seeded = await request.post(`${MOCK_API_URL}/__test/seed-owner-draft`);
  expect(seeded.ok()).toBeTruthy();
  await signIn(page, "other@example.com");

  await page.goto(`/library/${DRAFT_ID}`);
  await expect(
    page.getByRole("heading", { name: "This saved draft is no longer available." }),
  ).toBeVisible();
  await expect(page.getByText(/may not belong to this account/i)).toBeVisible();
  await expect(page.getByText("Owner-only synthetic draft.")).toHaveCount(0);
});
