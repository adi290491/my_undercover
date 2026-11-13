import { render, screen, within } from "@testing-library/react";
import { expect, it } from "vitest";
import { ClaimPage } from "../../dashboard/src/ClaimPage";
import { claimRoutes, history, policy, Refusal, stubApi } from "./testing";

it("shows the claim in full", async () => {
  stubApi(claimRoutes());
  render(<ClaimPage claimId="CLM-1001" />);
  expect(
    await screen.findByRole("heading", { name: "CLM-1001" }),
  ).toBeDefined();
  expect(screen.getByText("Trip delay for Maya Patel")).toBeDefined();
  expect(screen.getByText("Jun 18, 2026, Rome, Italy")).toBeDefined();
  expect(screen.getByText(/My flight home from Rome/)).toBeDefined();
  const items = within(screen.getByRole("region", { name: "Items claimed" }));
  expect(items.getByText("$245.00")).toBeDefined();
  expect(items.getByText("Accommodation")).toBeDefined();
  expect(items.getByText("Total claimed").closest("tr")?.textContent).toContain(
    "$420.00",
  );
  const documents = within(screen.getByRole("region", { name: "Documents" }));
  expect(documents.getByText("Meridian Air cancellation notice")).toBeDefined();
  expect(documents.getByText("Carrier report")).toBeDefined();
  expect(screen.getByRole("link", { name: "Back to the queue" })).toBeDefined();
});

it("shows the policy and the claim history", async () => {
  stubApi(claimRoutes());
  render(<ClaimPage claimId="CLM-1001" />);
  const panel = within(await screen.findByRole("region", { name: "Policy" }));
  expect(await panel.findByText("Premium")).toBeDefined();
  expect(panel.getByText("None")).toBeDefined();
  expect(panel.getByText("Rome, Italy, Jun 10 to Jun 18, 2026")).toBeDefined();
  expect(panel.getByText("$3,100.00")).toBeDefined();
  expect(
    panel.getByText("Apr 22, 2026, through Meridian Air checkout"),
  ).toBeDefined();
  const past = within(screen.getByRole("region", { name: "Claim history" }));
  expect(await past.findByText("CLM-0412")).toBeDefined();
  expect(
    past.getByText("Filed Aug 19, 2024. Approved, $140.00 paid."),
  ).toBeDefined();
});

it("names the add-ons and says when there is no history", async () => {
  stubApi({
    ...claimRoutes(),
    "/api/policies/POL-2001": {
      ...policy,
      add_ons: ["electronics_plus", "new_thing"],
    },
    "/api/customers/CUS-3001/claims": [],
  });
  render(<ClaimPage claimId="CLM-1001" />);
  expect(await screen.findByText("Electronics Plus, New thing")).toBeDefined();
  expect(await screen.findByText("No earlier claims.")).toBeDefined();
});

it("leaves out the amount paid on a declined claim", async () => {
  stubApi({
    ...claimRoutes(),
    "/api/customers/CUS-3001/claims": [
      { ...history[0], outcome: "declined", amount_paid: 0 },
    ],
  });
  render(<ClaimPage claimId="CLM-1001" />);
  expect(
    await screen.findByText("Filed Aug 19, 2024. Declined."),
  ).toBeDefined();
});

it("says when the claim isn't there", async () => {
  stubApi({
    "/api/claims/CLM-9999": new Refusal(404, "There is no claim CLM-9999."),
  });
  render(<ClaimPage claimId="CLM-9999" />);
  expect(await screen.findByText(/There is no claim CLM-9999\./)).toBeDefined();
  expect(screen.getByRole("link", { name: "Back to the queue" })).toBeDefined();
});

it("says when the policy or history can't be loaded", async () => {
  stubApi({
    "/api/claims/CLM-1001": claimRoutes()["/api/claims/CLM-1001"],
    "/api/policies/POL-2001": new Refusal(404, "There is no policy POL-2001."),
    "/api/customers/CUS-3001/claims": new Refusal(
      404,
      "There is no customer CUS-3001.",
    ),
  });
  render(<ClaimPage claimId="CLM-1001" />);
  expect(await screen.findByText("There is no policy POL-2001.")).toBeDefined();
  expect(
    await screen.findByText("There is no customer CUS-3001."),
  ).toBeDefined();
});
