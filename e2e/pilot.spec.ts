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
