import { render, screen, within } from "@testing-library/react";
import { expect, it } from "vitest";
import { Queue } from "../../dashboard/src/Queue";
import { Refusal, stubApi, summary } from "./testing";

const claims = [
  summary("CLM-1001"),
  summary("CLM-1002", {
    claim_type: "baggage",
    customer_name: "Tom Becker",
    amount_claimed: 1150,
    status: "awaiting_signoff",
  }),
  summary("CLM-1003", { status: "in_progress" }),
  summary("CLM-1004", { status: "decided" }),
  summary("CLM-1005", { status: "decided" }),
];

it("lists every claim with its details", async () => {
  stubApi({ "/api/claims": claims });
  render(<Queue />);
  const row = (await screen.findByRole("link", { name: "CLM-1002" })).closest(
    "tr",
  );
  if (!row) throw new Error("CLM-1002 has no row");
  const cells = within(row);
  expect(cells.getByText("Tom Becker")).toBeDefined();
  expect(cells.getByText("Baggage")).toBeDefined();
  expect(cells.getByText("$1,150.00")).toBeDefined();
  expect(cells.getByText("Jun 24, 2026")).toBeDefined();
  expect(cells.getByText("Awaiting sign-off")).toBeDefined();
  expect(
    screen.getByRole("link", { name: "CLM-1002" }).getAttribute("href"),
  ).toBe("#/claims/CLM-1002");
  expect(screen.getAllByRole("row")).toHaveLength(claims.length + 1);
});

it("counts the claims in each state", async () => {
  stubApi({ "/api/claims": claims });
  render(<Queue />);
  const counts = within(await screen.findByLabelText("Claims by status"));
  const count = (name: string) =>
    counts.getByText(name).parentElement?.querySelector(".count-number")
      ?.textContent;
  expect(count("Waiting")).toBe("1");
  expect(count("In progress")).toBe("1");
  expect(count("Awaiting sign-off")).toBe("1");
  expect(count("Decided")).toBe("2");
});

it("says when the queue can't be loaded", async () => {
  stubApi({ "/api/claims": new Refusal(500, "The database is locked.") });
  render(<Queue />);
  expect(
    await screen.findByText(
      "The queue couldn't be loaded: The database is locked.",
    ),
  ).toBeDefined();
});

it("says when a request fails without a reason", async () => {
  stubApi({
    "/api/claims": () => new Refusal(422, [{ msg: "Field required" }]),
  });
  render(<Queue />);
  expect(
    await screen.findByText(
      "The queue couldn't be loaded: The request failed with status 422.",
    ),
  ).toBeDefined();
});
