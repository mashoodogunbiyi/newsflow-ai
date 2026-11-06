import { expect, type APIRequestContext, type Page } from "@playwright/test";

export const MOCK_API_URL = "http://127.0.0.1:4100";
export const DRAFT_ID = "50000000-0000-4000-8000-000000000005";

export async function resetTestState(request: APIRequestContext) {
  const response = await request.post(`${MOCK_API_URL}/__test/reset`);
  expect(response.ok()).toBeTruthy();
}

export async function signIn(
  page: Page,
  email = "owner@example.com",
  password = "TestPassword123!",
) {
  await page.goto("/login");
  await page.getByLabel("Email address").fill(email);
  await page.getByLabel("Password", { exact: true }).fill(password);
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page).toHaveURL(/\/dashboard$/);
  await expect(
    page.getByRole("heading", { name: "From trusted link to thoughtful post." }),
  ).toBeVisible();
}
