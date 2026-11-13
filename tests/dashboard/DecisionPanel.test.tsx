import { render, screen, within } from "@testing-library/react";
import { expect, it } from "vitest";
import { ClaimPage } from "../../dashboard/src/ClaimPage";
import { claimRoutes, decision, stubApi } from "./testing";

async function decisionPanel() {
  return within(
    await screen.findByRole("region", { name: "The agent's decision" }),
  );
}

it("shows a paid approval with its reasons and section", async () => {
  stubApi(
    claimRoutes({
      status: "decided",
      decision: decision(),
      payment: { amount: 420, paid_at: "2026-11-13T15:04:09+00:00" },
    }),
  );
  render(<ClaimPage claimId="CLM-1001" />);
  const panel = await decisionPanel();
  expect(panel.getByText("Approved")).toBeDefined();
  expect(
    panel.getByText(/The flight was canceled for a crew problem/),
  ).toBeDefined();
  expect(
    panel.getByRole("heading", { name: "Section 3, Trip Delay" }),
  ).toBeDefined();
  expect(panel.getByText(/We pay when your carrier delays you/)).toBeDefined();
  const paid = panel.getByText("Paid").nextElementSibling?.textContent;
  expect(paid).toContain("$420.00");
  expect(paid).toContain("2026");
  expect(panel.queryByText("Needs sign-off")).toBeNull();
});

it("shows an approval the agent hasn't paid yet", async () => {
  stubApi(claimRoutes({ status: "in_progress", decision: decision() }));
  render(<ClaimPage claimId="CLM-1001" />);
  const panel = await decisionPanel();
  expect(panel.getByText("Paid").nextElementSibling?.textContent).toBe(
    "Not yet",
  );
});

it("flags a payout waiting for sign-off, then shows who signed it off", async () => {
  const big = decision({ payout: 1150 });
  stubApi(claimRoutes({ status: "awaiting_signoff", decision: big }));
  const { unmount } = render(<ClaimPage claimId="CLM-1001" />);
  const panel = await decisionPanel();
  expect(panel.getByText("Needs sign-off")).toBeDefined();
  expect(
    panel.getByText(/This payout of \$1,150\.00 is over the approval limit/),
  ).toBeDefined();
  expect(panel.getByText("Paid").nextElementSibling?.textContent).toBe(
    "Waiting for a handler's sign-off",
  );
  unmount();

  stubApi(
    claimRoutes({
      status: "decided",
      decision: big,
      payment: { amount: 1150, paid_at: "2026-11-13T16:00:00+00:00" },
      sign_off: {
        handler_id: "HND-01",
        handler_name: "Dana Whitfield",
        signed_at: "2026-11-13T16:00:00+00:00",
      },
    }),
  );
  render(<ClaimPage claimId="CLM-1001" />);
  const signed = await decisionPanel();
  expect(signed.getByText(/Dana Whitfield/)).toBeDefined();
  expect(signed.queryByText("Needs sign-off")).toBeNull();
});

it("shows a decline without a payout", async () => {
  stubApi(
    claimRoutes({
      status: "decided",
      decision: decision({ decision: "decline", payout: 0 }),
    }),
  );
  render(<ClaimPage claimId="CLM-1001" />);
  const panel = await decisionPanel();
  expect(panel.getByText("Declined")).toBeDefined();
  expect(panel.queryByText("Paid")).toBeNull();
  expect(panel.queryByText("$0.00")).toBeNull();
});

it("has no decision panel before a decision", async () => {
  stubApi(claimRoutes());
  render(<ClaimPage claimId="CLM-1001" />);
  await screen.findByRole("heading", { name: "CLM-1001" });
  expect(
    screen.queryByRole("region", { name: "The agent's decision" }),
  ).toBeNull();
});
