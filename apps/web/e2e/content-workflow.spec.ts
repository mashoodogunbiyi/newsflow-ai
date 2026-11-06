import { expect, test } from "@playwright/test";

import { resetTestState, signIn } from "./helpers";

test.beforeEach(async ({ request }) => resetTestState(request));

test("completes article-to-generation-to-private-library lifecycle", async ({ context, page }) => {
  await context.grantPermissions(["clipboard-read", "clipboard-write"]);
  await signIn(page);

  await page
    .getByLabel("Search URL")
    .fill("https://example.invalid/newsflow-ai/synthetic-technology-update");
  await page.getByRole("button", { name: "Use this article" }).click();
  await expect(
    page.getByRole("heading", { name: "Review the source before generating." }),
  ).toBeVisible();

  await page.getByRole("button", { name: "Generate LinkedIn draft" }).click();
  await expect(page.getByText("Your private draft has been generated.")).toBeVisible();

  const reviewedText = "A human-reviewed synthetic LinkedIn draft with preserved attribution.";
  await page.getByRole("textbox", { name: "LinkedIn draft text" }).fill(reviewedText);
  await expect(page.getByTestId("draft-preview")).toHaveText(reviewedText);

  await page.getByRole("button", { name: "Generate image" }).click();
  await expect(page.getByText("Your private illustration is ready for review.")).toBeVisible();
  await expect(page.getByRole("button", { name: "Regenerate image" })).toBeVisible();
  await page.getByRole("button", { name: "Regenerate image" }).click();
  await expect(page.getByRole("radio", { name: "Use original in preview" })).toBeVisible();
  await expect(page.getByRole("radio", { name: "Use version 2 in preview" })).toBeChecked();
  await expect(page.getByRole("textbox", { name: "LinkedIn draft text" })).toHaveValue(
    reviewedText,
  );

  await page.getByRole("button", { name: "Save to library" }).click();
  await expect(page).toHaveURL(/\/library\/50000000-0000-4000-8000-000000000005$/);
  await expect(
    page.getByRole("heading", { name: "Continue editing your saved draft." }),
  ).toBeVisible();
  await expect(page.getByRole("textbox", { name: "LinkedIn draft text" })).toHaveValue(
    reviewedText,
  );
  await expect(
    page.getByRole("img", { name: /AI-generated editorial illustration/i }),
  ).toBeVisible();

  await page.getByRole("button", { name: "Copy Post" }).click();
  await expect(
    page.getByText("Current edited post copied with its line breaks preserved."),
  ).toBeVisible();
  await expect.poll(() => page.evaluate(() => navigator.clipboard.readText())).toBe(reviewedText);

  await page.getByRole("button", { name: "Download Image" }).click();
  await expect(page.getByText("The AI-generated illustration download has started.")).toBeVisible();

  await page.getByRole("button", { name: "Delete draft" }).click();
  await expect(page.getByRole("dialog")).toBeVisible();
  await page.getByRole("button", { name: "Delete permanently" }).click();
  await expect(page).toHaveURL(/\/library\?deleted=1$/);
  await expect(page.getByText("You have not saved any drafts yet.")).toBeVisible();
  await expect(page.getByText(/secure cleanup has started/i)).toBeVisible();
});
