import { cleanup, render, screen, within } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { Instructions } from "./Instructions";
import { Queue } from "./Queue";
import { Failure, stubApi, summary } from "./testing";

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

it("shows every claim with its status and the counts", async () => {
  stubApi({
    "GET /api/claims": [
      summary,
      { ...summary, claim_id: "CLM-1002", status: "decided" },
      { ...summary, claim_id: "CLM-1003", status: "awaiting_signoff" },
    ],
  });
  render(<Queue />);
  const claims = await screen.findByRole("list", { name: "Claims" });
  const rows = within(claims).getAllByRole("link");
  expect(rows).toHaveLength(3);
  expect(rows[0]?.getAttribute("href")).toBe("#/claims/CLM-1001");
  expect(within(claims).getAllByText("$1,420.00")).toHaveLength(3);
  expect(within(claims).getByText("Awaiting sign-off")).toBeDefined();
  const counts = screen.getByRole("list", { name: "Claims by status" });
  expect(counts.textContent).toBe(
    "1Waiting0In progress1Awaiting sign-off1Decided",
  );
});

it("shows when the queue cannot load", async () => {
  stubApi({ "GET /api/claims": new Failure(500, "The backend is down") });
  render(<Queue />);
  expect((await screen.findByRole("alert")).textContent).toBe(
    "Error: The backend is down",
  );
});

it("shows the agent's instructions, read only", async () => {
  stubApi({ "GET /api/instructions": { instructions: "# Decide claims" } });
  render(<Instructions />);
  expect(await screen.findByText("# Decide claims")).toBeDefined();
  expect(screen.queryByRole("textbox")).toBeNull();
  expect(screen.queryByRole("button")).toBeNull();
});

it("shows when the instructions cannot load", async () => {
  stubApi({});
  render(<Instructions />);
  expect(await screen.findByRole("alert")).toBeDefined();
});
