import { expect, test } from "@playwright/test";

test("the queue shows every claim, all waiting", async ({ page }) => {
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: "Claims queue" }),
  ).toBeVisible();
  await expect(page.locator(".queue-table tbody tr")).toHaveCount(25);
  const waiting = page
    .locator(".count")
    .filter({ has: page.getByText("Waiting", { exact: true }) });
  await expect(waiting.locator(".count-number")).toHaveText("25");
  await expect(page.getByRole("row", { name: /CLM-1001/ })).toContainText(
    "$420.00",
  );
});

test("a claim opens from the queue, and the instructions are read only", async ({
  page,
}) => {
  await page.goto("/");
  await page.getByRole("link", { name: "CLM-1001" }).click();
  await expect(page).toHaveURL(/#\/claims\/CLM-1001$/);
  await expect(page.getByText(/My flight home from Rome/)).toBeVisible();
  await expect(
    page.getByRole("region", { name: "Items claimed" }),
  ).toContainText("$420.00");
  await expect(page.getByRole("region", { name: "Policy" })).toContainText(
    "Rome, Italy, Jun 10 to Jun 18, 2026",
  );
  await expect(
    page.getByRole("region", { name: "Claim history" }),
  ).toContainText("CLM-0412");

  await page.getByRole("link", { name: "Instructions" }).click();
  await expect(
    page.getByRole("heading", {
      name: "How the UnderCover Agent works a claim",
    }),
  ).toBeVisible();
  await expect(page.locator("textarea, input, [contenteditable]")).toHaveCount(
    0,
  );
});
