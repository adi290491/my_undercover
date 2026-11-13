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

test("the agent runs on a claim from the dashboard and pays it", async ({
  page,
}) => {
  await page.goto("/#/claims/CLM-1001");
  await page.getByRole("button", { name: "Run the agent" }).click();
  const steps = page.getByRole("region", { name: "The agent's steps" });
  await expect(steps.getByText("Read the claim CLM-1001")).toBeVisible();
  await expect(steps.getByText("Pay $420.00")).toBeVisible();
  await expect(page.locator(".claim-title .badge")).toHaveText("Decided");
  const decision = page.getByRole("region", { name: "The agent's decision" });
  await expect(decision).toContainText("Approved");
  await expect(
    decision.getByText("Paid").locator("xpath=following-sibling::dd[1]"),
  ).toContainText("$420.00");
});
