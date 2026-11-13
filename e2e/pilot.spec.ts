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

test("a payout over $1,000 waits for a handler, who signs it off", async ({
  page,
}) => {
  await page.goto("/#/claims/CLM-1002");
  await page.getByRole("button", { name: "Run the agent" }).click();
  const badge = page.locator(".claim-title .badge");
  await expect(badge).toHaveText("Awaiting sign-off");
  const refused = page.locator(".step.refused");
  await expect(refused).toContainText("Refused (403): The payout of $1,150.00");
  await expect(page.getByText("Needs sign-off")).toBeVisible();

  const signOff = page.getByRole("region", { name: "Sign off the payout" });
  const button = signOff.getByRole("button", {
    name: "Sign off and pay $1,150.00",
  });
  await expect(button).toBeDisabled();
  await signOff
    .getByLabel("Handler")
    .selectOption({ label: "Dana Whitfield, Senior Claims Handler" });
  await button.click();

  await expect(badge).toHaveText("Decided");
  await expect(signOff).toHaveCount(0);
  const decision = page.getByRole("region", { name: "The agent's decision" });
  const value = (label: string) =>
    decision
      .getByText(label, { exact: true })
      .locator("xpath=following-sibling::dd[1]");
  await expect(value("Paid")).toContainText("$1,150.00");
  await expect(value("Signed off")).toContainText("Dana Whitfield");

  await page.getByRole("link", { name: "Back to the queue" }).click();
  await expect(
    page.getByRole("row", { name: /CLM-1002/ }).locator(".badge"),
  ).toHaveText("Decided");
});
