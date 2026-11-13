import { render, screen, within } from "@testing-library/react";
import { expect, it } from "vitest";
import { runEnded } from "../../dashboard/src/runs";
import { Steps } from "../../dashboard/src/Steps";
import { Refusal, step, stubApi } from "./testing";

async function run(name: string) {
  const heading = await screen.findByRole("heading", { name });
  if (!heading.parentElement) throw new Error(`${name} has no steps`);
  return within(heading.parentElement);
}

it("shows each run's steps in order", async () => {
  stubApi({
    "/api/claims/CLM-1001/steps": [
      step(1, "tool_call", "Read the claim CLM-1001"),
      step(2, "error", "The run ended without a decision."),
      step(3, "tool_call", "Read the claim CLM-1001", "thread-2"),
      step(4, "tool_result", '{"claim_id": "CLM-1001"}', "thread-2"),
      step(
        5,
        "tool_result",
        "Refused (403): The payout needs a sign-off.",
        "thread-2",
      ),
      step(6, "message", "Approved, waiting for sign-off.", "thread-2"),
    ],
  });
  render(<Steps claimId="CLM-1001" claimInProgress={false} />);
  const first = await run("Run 1");
  expect(first.getAllByRole("listitem")).toHaveLength(2);
  const second = await run("Run 2");
  const rows = second.getAllByRole("listitem");
  expect(
    rows.map((row) => row.querySelector(".step-kind")?.textContent),
  ).toEqual(["Action", "Result", "Refused", "Agent"]);
  expect(second.getByText("Show the result").closest("details")?.open).toBe(
    false,
  );
  expect(rows[2]?.className).toContain("refused");
  expect(first.getAllByRole("listitem")[1]?.className).toContain("error");
  expect(
    second.getByText("Refused (403): The payout needs a sign-off."),
  ).toBeDefined();
});

it("says when the agent hasn't worked the claim", async () => {
  stubApi({ "/api/claims/CLM-1001/steps": [] });
  render(<Steps claimId="CLM-1001" claimInProgress={false} />);
  expect(
    await screen.findByText("The agent hasn't worked on this claim yet."),
  ).toBeDefined();
});

it("says when the steps can't be loaded", async () => {
  stubApi({
    "/api/claims/CLM-1001/steps": new Refusal(500, "Something broke."),
  });
  render(<Steps claimId="CLM-1001" claimInProgress={false} />);
  expect(await screen.findByText("Something broke.")).toBeDefined();
});

it("knows when the latest run has ended", () => {
  expect(runEnded(undefined)).toBe(true);
  expect(runEnded([])).toBe(true);
  expect(runEnded([step(1, "tool_call", "Pay $420.00")])).toBe(false);
  expect(runEnded([step(1, "tool_result", "Refused (403): Wait.")])).toBe(
    false,
  );
  expect(runEnded([step(1, "message", "Done.")])).toBe(true);
  expect(runEnded([step(1, "error", "The run failed.")])).toBe(true);
});
