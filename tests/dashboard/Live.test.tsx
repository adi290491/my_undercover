import { act, fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, expect, it, vi } from "vitest";
import type { Claim } from "../../dashboard/src/api";
import { ClaimPage } from "../../dashboard/src/ClaimPage";
import { Queue } from "../../dashboard/src/Queue";
import {
  claim,
  claimRoutes,
  decision,
  Refusal,
  step,
  stubApi,
  summary,
  type Call,
} from "./testing";

beforeEach(() => {
  vi.useFakeTimers({ shouldAdvanceTime: true });
});

async function wait(ms: number) {
  await act(() => vi.advanceTimersByTimeAsync(ms));
}

function gets(calls: Call[], path: string) {
  return calls.filter((c) => c.method === "GET" && c.path === path).length;
}

it("runs the agent and follows its steps live", async () => {
  let phase = 0;
  const claims: Claim[] = [
    claim(),
    claim({ status: "in_progress", thread_id: "thread-1" }),
    claim({ status: "in_progress", thread_id: "thread-1" }),
    claim({
      status: "decided",
      thread_id: "thread-1",
      decision: decision(),
      payment: { amount: 420, paid_at: "2026-11-13T15:04:09+00:00" },
    }),
  ];
  const steps = [
    [],
    [step(1, "tool_call", "Read the claim CLM-1001")],
    [
      step(1, "tool_call", "Read the claim CLM-1001"),
      step(2, "tool_result", "{}"),
    ],
    [
      step(1, "tool_call", "Read the claim CLM-1001"),
      step(2, "tool_result", "{}"),
      step(3, "message", "Approved CLM-1001 in full and paid it."),
    ],
  ];
  const calls = stubApi({
    ...claimRoutes(),
    "/api/claims/CLM-1001": () => claims[phase],
    "/api/claims/CLM-1001/steps": () => steps[phase],
    "POST /api/claims/CLM-1001/run": () => {
      phase = 1;
      return { claim_id: "CLM-1001", thread_id: "thread-1" };
    },
  });
  render(<ClaimPage claimId="CLM-1001" />);
  expect(
    await screen.findByText("The agent hasn't worked on this claim yet."),
  ).toBeDefined();

  fireEvent.click(screen.getByRole("button", { name: "Run the agent" }));
  expect(await screen.findByText("Read the claim CLM-1001")).toBeDefined();
  expect(screen.getByText(/The agent is working on this claim/)).toBeDefined();
  expect(screen.getByText("In progress")).toBeDefined();
  expect(screen.queryByRole("button", { name: "Run the agent" })).toBeNull();

  phase = 2;
  await wait(1000);
  expect(await screen.findByText("Show the result")).toBeDefined();

  phase = 3;
  await wait(1000);
  expect(
    await screen.findByText("Approved CLM-1001 in full and paid it."),
  ).toBeDefined();
  expect(screen.getByText("Decided", { selector: ".badge" })).toBeDefined();
  expect(
    screen.getByRole("region", { name: "The agent's decision" }),
  ).toBeDefined();
  expect(screen.queryByText(/The agent is working on this claim/)).toBeNull();

  const claimGets = gets(calls, "/api/claims/CLM-1001");
  const stepGets = gets(calls, "/api/claims/CLM-1001/steps");
  await wait(5000);
  expect(gets(calls, "/api/claims/CLM-1001")).toBe(claimGets);
  expect(gets(calls, "/api/claims/CLM-1001/steps")).toBe(stepGets);
});

it("keeps following the steps until the run's final message", async () => {
  let ended = false;
  const paid = [
    step(1, "tool_call", "Pay $420.00"),
    step(2, "tool_result", "{}"),
  ];
  const calls = stubApi({
    ...claimRoutes({
      status: "decided",
      thread_id: "thread-1",
      decision: decision(),
      payment: { amount: 420, paid_at: "2026-11-13T15:04:09+00:00" },
    }),
    "/api/claims/CLM-1001/steps": () =>
      ended ? [...paid, step(3, "message", "Approved and paid.")] : paid,
  });
  render(<ClaimPage claimId="CLM-1001" />);
  expect(await screen.findByText("Pay $420.00")).toBeDefined();
  expect(screen.getByText(/The agent is working on this claim/)).toBeDefined();
  ended = true;
  await wait(1000);
  expect(await screen.findByText("Approved and paid.")).toBeDefined();
  expect(screen.queryByText(/The agent is working on this claim/)).toBeNull();
  const stepGets = gets(calls, "/api/claims/CLM-1001/steps");
  await wait(3000);
  expect(gets(calls, "/api/claims/CLM-1001/steps")).toBe(stepGets);
});

it("loads the steps of a run that finished between two refreshes", async () => {
  let finished = false;
  stubApi({
    ...claimRoutes(),
    "/api/claims/CLM-1001": () =>
      finished
        ? claim({
            status: "awaiting_signoff",
            thread_id: "thread-1",
            decision: decision({ payout: 1150 }),
          })
        : claim(),
    "/api/claims/CLM-1001/steps": () =>
      finished
        ? [
            step(1, "tool_call", "Pay $1,150.00"),
            step(2, "tool_result", "Refused (403): Wait for a sign-off."),
            step(3, "message", "Approved; the payment waits for sign-off."),
          ]
        : [],
  });
  render(<ClaimPage claimId="CLM-1001" />);
  expect(
    await screen.findByText("The agent hasn't worked on this claim yet."),
  ).toBeDefined();
  finished = true;
  await wait(2000);
  expect(
    await screen.findByText("Approved; the payment waits for sign-off."),
  ).toBeDefined();
  expect(screen.getByText("Refused", { selector: ".step-kind" })).toBeDefined();
});

it("picks up a run started elsewhere on a waiting claim", async () => {
  let started = false;
  stubApi({
    ...claimRoutes(),
    "/api/claims/CLM-1001": () =>
      started ? claim({ status: "in_progress", thread_id: "cli" }) : claim(),
  });
  render(<ClaimPage claimId="CLM-1001" />);
  expect(
    await screen.findByRole("button", { name: "Run the agent" }),
  ).toBeDefined();
  started = true;
  await wait(2000);
  expect(await screen.findByText("In progress")).toBeDefined();
});

it("says when the agent can't be started", async () => {
  stubApi({
    ...claimRoutes(),
    "POST /api/claims/CLM-1001/run": new Refusal(
      409,
      "CLM-1001 is in progress, so it can't be run.",
    ),
  });
  render(<ClaimPage claimId="CLM-1001" />);
  fireEvent.click(await screen.findByRole("button", { name: "Run the agent" }));
  expect(
    await screen.findByText("CLM-1001 is in progress, so it can't be run."),
  ).toBeDefined();
  const button = screen.getByRole("button", { name: "Run the agent" });
  expect(button.hasAttribute("disabled")).toBe(false);
});

it("keeps showing the claim when a refresh fails", async () => {
  let failing = false;
  stubApi({
    ...claimRoutes(),
    "/api/claims/CLM-1001": () =>
      failing
        ? new Refusal(500, "The backend is restarting.")
        : claim({ status: "in_progress", thread_id: "thread-1" }),
  });
  render(<ClaimPage claimId="CLM-1001" />);
  expect(await screen.findByText("In progress")).toBeDefined();
  failing = true;
  await wait(1000);
  expect(screen.getByRole("heading", { name: "CLM-1001" })).toBeDefined();
  failing = false;
  await wait(1000);
  expect(screen.getByText("In progress")).toBeDefined();
});

it("refreshes the queue every two seconds", async () => {
  let status: "waiting" | "in_progress" = "waiting";
  const calls = stubApi({
    "/api/claims": () => [summary("CLM-1001", { status })],
  });
  render(<Queue />);
  const counts = await screen.findByLabelText("Claims by status");
  expect(counts.textContent).toContain("Waiting1");
  status = "in_progress";
  await wait(2000);
  expect(counts.textContent).toContain("In progress1");
  expect(gets(calls, "/api/claims")).toBe(2);
});
