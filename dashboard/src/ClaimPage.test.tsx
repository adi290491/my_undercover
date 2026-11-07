import {
  cleanup,
  fireEvent,
  render,
  screen,
  within,
} from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import type { Claim } from "./api";
import { ClaimPage } from "./ClaimPage";
import { claim, claimRoutes, Failure, type Routes, stubApi } from "./testing";

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

const decided: Claim = {
  ...claim,
  status: "decided",
  decision: {
    decision: "approve",
    payout: 1420,
    reason: "Section 3 covers a canceled flight.",
    policy_section: "Section 3, Trip Delay",
    decided_at: "2026-11-06T10:00:00+00:00",
  },
  payment: { amount: 1420, paid_at: "2026-11-06T10:05:00+00:00" },
  sign_off: {
    handler_id: "HND-01",
    handler_name: "Dana Whitfield",
    signed_at: "2026-11-06T10:05:00+00:00",
  },
};

it("shows the claim in full", async () => {
  stubApi(claimRoutes(claim));
  render(<ClaimPage claimId="CLM-1001" />);
  expect(
    await screen.findByText("My flight home from Rome was canceled."),
  ).toBeDefined();
  const items = screen.getByRole("region", { name: "Items" });
  expect(within(items).getByText("$1,245.00")).toBeDefined();
  expect(within(items).getByText("$1,420.00")).toBeDefined();
  expect(screen.getByText("Hotel Aurelia, one night.")).toBeDefined();
  expect(
    screen.getByText("The agent has not decided this claim yet."),
  ).toBeDefined();
  const policy = await screen.findByRole("region", { name: "Policy" });
  expect(within(policy).getByText("Electronics plus")).toBeDefined();
  expect(within(policy).getByText("$3,100.00")).toBeDefined();
  const history = await screen.findByRole("region", { name: "Claim history" });
  expect(within(history).getByText("CLM-0412")).toBeDefined();
});

it("shows the decision with its payment and sign-off", async () => {
  stubApi(claimRoutes(decided));
  render(<ClaimPage claimId="CLM-1001" />);
  const decision = await screen.findByRole("region", { name: "Decision" });
  expect(within(decision).getByText("Approve")).toBeDefined();
  expect(
    within(decision).getByText("Section 3 covers a canceled flight."),
  ).toBeDefined();
  expect(within(decision).getByText("Section 3, Trip Delay")).toBeDefined();
  expect(decision.textContent).toContain("Paid $1,420.00 on Nov 6, 2026");
  expect(decision.textContent).toContain("Signed off by Dana Whitfield");
  expect(screen.queryByRole("button", { name: "Run the agent" })).toBeNull();
});

it("runs the agent on a waiting claim", async () => {
  const routes: Routes = {
    ...claimRoutes(claim),
    "POST /api/claims/CLM-1001/run": { thread_id: "t-1" },
  };
  const fetchMock = stubApi(routes);
  render(<ClaimPage claimId="CLM-1001" />);
  const run = await screen.findByRole("button", { name: "Run the agent" });
  routes["GET /api/claims/CLM-1001"] = decided;
  fireEvent.click(run);
  expect(await screen.findByText("Approve")).toBeDefined();
  expect(fetchMock).toHaveBeenCalledWith(
    "/api/claims/CLM-1001/run",
    expect.objectContaining({ method: "POST" }),
  );
});

it("shows why the agent could not start", async () => {
  stubApi({
    ...claimRoutes(claim),
    "POST /api/claims/CLM-1001/run": new Failure(409, "Claim is in_progress"),
  });
  render(<ClaimPage claimId="CLM-1001" />);
  fireEvent.click(await screen.findByRole("button", { name: "Run the agent" }));
  expect((await screen.findByRole("alert")).textContent).toBe(
    "Error: Claim is in_progress",
  );
});

it("shows when the claim cannot load", async () => {
  stubApi({});
  render(<ClaimPage claimId="CLM-9999" />);
  expect((await screen.findByRole("alert")).textContent).toBe(
    "Error: No GET /api/claims/CLM-9999",
  );
});
