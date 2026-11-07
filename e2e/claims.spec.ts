import { expect, test } from "@playwright/test";

test("the queue shows every claim and where it stands", async ({ page }) => {
  await page.goto("/");
  const claims = page.getByRole("list", { name: "Claims" });
  await expect(claims.getByRole("link")).toHaveCount(25);
  await expect(claims.getByText("CLM-1001")).toBeVisible();
  await expect(
    page.getByRole("list", { name: "Claims by status" }),
  ).toContainText("Waiting");
});

test("the agent decides a claim and pays it", async ({ page }) => {
  await page.goto("/#/claims/CLM-1001");
  await page.getByRole("button", { name: "Run the agent" }).click();
  const steps = page.getByRole("region", { name: "Agent steps" });
  await expect(steps.getByText("get_claim({})")).toBeVisible();
  await expect(steps.getByText("Approved, payout $420.00.")).toBeVisible();
  await expect(page.getByText("Decided", { exact: true })).toBeVisible();
  const decision = page.getByRole("region", { name: "Decision" });
  await expect(decision.getByText("Approve", { exact: true })).toBeVisible();
  await expect(decision).toContainText("Paid $420.00");
});

test("a payout over the limit waits for a handler", async ({ page }) => {
  await page.goto("/#/claims/CLM-1002");
  await page.getByRole("button", { name: "Run the agent" }).click();
  await expect(page.getByText("Awaiting sign-off")).toBeVisible();
  const steps = page.getByRole("region", { name: "Agent steps" });
  await expect(steps).toContainText("waits for a handler's sign-off");
  const signOff = page.getByRole("region", { name: "Sign-off" });
  await expect(signOff).toContainText("The payout of $1,150.00 is over");
  await signOff.getByRole("combobox").selectOption("Marcus Oyelaran");
  await signOff.getByRole("button", { name: "Sign off and pay" }).click();
  const decision = page.getByRole("region", { name: "Decision" });
  await expect(decision).toContainText("Paid $1,150.00");
  await expect(decision).toContainText("Signed off by Marcus Oyelaran");
  await expect(page.getByText("Decided", { exact: true })).toBeVisible();
});

test("the agent's instructions are shown read only", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("link", { name: "Agent instructions" }).click();
  await expect(page.getByText("# The UnderCover Agent")).toBeVisible();
  await expect(page.getByRole("textbox")).toHaveCount(0);
});
