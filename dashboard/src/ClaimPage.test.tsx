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
import { clock } from "./format";
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

const awaiting: Claim = {
  ...decided,
  status: "awaiting_signoff",
  payment: null,
  sign_off: null,
};

const handlers = [
  { handler_id: "HND-01", name: "Dana Whitfield", role: "Senior" },
  { handler_id: "HND-02", name: "Marcus Oyelaran", role: "Handler" },
];

it("shows each step the agent took", async () => {
  stubApi({
    ...claimRoutes(decided),
    "GET /api/claims/CLM-1001/steps": [
      {
        step_id: 1,
        at: "2026-11-06T10:00:01+00:00",
        kind: "tool_call",
        text: "get_claim({})",
      },
      {
        step_id: 2,
        at: "2026-11-06T10:00:02+00:00",
        kind: "tool_result",
        text: 'pay_claim: {"detail":"A payout over $1,000.00 waits"}',
      },
      {
        step_id: 3,
        at: "2026-11-06T10:00:03+00:00",
        kind: "message",
        text: "Approved.",
      },
      {
        step_id: 4,
        at: "2026-11-06T10:00:04+00:00",
        kind: "error",
        text: "The agent stopped: down",
      },
    ],
  });
  render(<ClaimPage claimId="CLM-1001" />);
  const steps = await screen.findByRole("region", { name: "Agent steps" });
  expect(await within(steps).findByText("get_claim({})")).toBeDefined();
  expect(within(steps).getByText("pay_claim")).toBeDefined();
  expect(steps.textContent).toContain(
    '{"detail":"A payout over $1,000.00 waits"}',
  );
  expect(within(steps).getByText("Approved.")).toBeDefined();
  expect(within(steps).getByText("Stopped")).toBeDefined();
  expect(
    within(steps).getByText(clock("2026-11-06T10:00:01+00:00")),
  ).toBeDefined();
});

it("signs off a payout over the limit", async () => {
  const routes: Routes = {
    ...claimRoutes(awaiting),
    "GET /api/handlers": handlers,
    "POST /api/claims/CLM-1001/sign-off": decided,
  };
  const fetchMock = stubApi(routes);
  render(<ClaimPage claimId="CLM-1001" />);
  const panel = await screen.findByRole("region", { name: "Sign-off" });
  expect(panel.textContent).toContain("The payout of $1,420.00 is over");
  const button = within(panel).getByRole("button", {
    name: "Sign off and pay",
  });
  expect(button.hasAttribute("disabled")).toBe(true);
  await within(panel).findByRole("option", { name: "Marcus Oyelaran" });
  fireEvent.change(within(panel).getByRole("combobox"), {
    target: { value: "HND-02" },
  });
  routes["GET /api/claims/CLM-1001"] = decided;
  fireEvent.click(button);
  expect(await screen.findByText("Signed off by Dana Whitfield")).toBeDefined();
  expect(screen.queryByRole("region", { name: "Sign-off" })).toBeNull();
  expect(fetchMock).toHaveBeenCalledWith(
    "/api/claims/CLM-1001/sign-off",
    expect.objectContaining({ body: '{"handler_id":"HND-02"}' }),
  );
});

it("shows why a sign-off failed", async () => {
  stubApi({
    ...claimRoutes(awaiting),
    "GET /api/handlers": handlers,
    "POST /api/claims/CLM-1001/sign-off": new Failure(403, "Not allowed"),
  });
  render(<ClaimPage claimId="CLM-1001" />);
  await screen.findByRole("option", { name: "Dana Whitfield" });
  fireEvent.change(screen.getByRole("combobox"), {
    target: { value: "HND-01" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Sign off and pay" }));
  expect((await screen.findByRole("alert")).textContent).toBe(
    "Error: Not allowed",
  );
});

it("follows a claim while the agent works on it", async () => {
  const routes: Routes = claimRoutes({ ...claim, status: "in_progress" });
  stubApi(routes);
  render(<ClaimPage claimId="CLM-1001" />);
  expect(await screen.findByText("In progress")).toBeDefined();
  routes["GET /api/claims/CLM-1001"] = decided;
  expect(
    await screen.findByText("Approve", {}, { timeout: 3000 }),
  ).toBeDefined();
});

it("waits for the run to start before it can be run again", async () => {
  const routes: Routes = {
    ...claimRoutes(claim),
    "POST /api/claims/CLM-1001/run": { thread_id: "t-1" },
  };
  stubApi(routes);
  render(<ClaimPage claimId="CLM-1001" />);
  fireEvent.click(await screen.findByRole("button", { name: "Run the agent" }));
  const starting = await screen.findByRole("button", {
    name: "Starting the agent",
  });
  expect(starting.hasAttribute("disabled")).toBe(true);
  routes["GET /api/claims/CLM-1001"] = { ...claim, thread_id: "t-1" };
  expect(
    await screen.findByRole(
      "button",
      { name: "Run the agent" },
      { timeout: 3000 },
    ),
  ).toBeDefined();
});
