import { expect, test } from "@playwright/test";

import { resetTestState, signIn } from "./helpers";

test.beforeEach(async ({ request }) => resetTestState(request));

test("protects workspace routes and authenticates a test user", async ({ page }) => {
  await page.goto("/dashboard");
  await expect(page).toHaveURL(/\/login\?reason=authentication_required$/);
  await expect(page.getByText("Sign in to continue to your dashboard.")).toBeVisible();

  await signIn(page);
  await page.reload();
  await expect(page.getByText("owner@example.com")).toBeVisible();
});

test("rejects invalid credentials with a controlled generic message", async ({ page }) => {
  await page.goto("/login");
  await page.getByLabel("Email address").fill("owner@example.com");
  await page.getByLabel("Password", { exact: true }).fill("WrongPassword123!");
  await page.getByRole("button", { name: "Sign in" }).click();

  await expect(page.getByText("Invalid email or password.", { exact: true })).toBeVisible();
  await expect(page).toHaveURL(/\/login$/);
});
