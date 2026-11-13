import { render, screen } from "@testing-library/react";
import { expect, it } from "vitest";
import { App } from "../../dashboard/src/App";
import { claimRoutes, stubApi, summary } from "./testing";

it("shows the queue at the root", async () => {
  stubApi({ "/api/claims": [summary("CLM-1001")] });
  render(<App />);
  expect(
    await screen.findByRole("heading", { name: "Claims queue" }),
  ).toBeDefined();
  expect(
    screen.getByRole("link", { name: "Queue" }).getAttribute("aria-current"),
  ).toBe("page");
  expect(
    screen.getByText("Travel claims, handled straight through"),
  ).toBeDefined();
});

it("says when there is no page at an address", async () => {
  stubApi({});
  window.location.hash = "#/nowhere";
  render(<App />);
  expect(await screen.findByText(/There's no page here/)).toBeDefined();
  expect(screen.getByRole("link", { name: "Back to the queue" })).toBeDefined();
});

it("opens a claim and the instructions from their addresses", async () => {
  stubApi({
    ...claimRoutes(),
    "/api/instructions": { text: "# Instructions\n\nRead the claim." },
  });
  window.location.hash = "#/claims/CLM-1001";
  render(<App />);
  expect(
    await screen.findByRole("heading", { name: "CLM-1001" }),
  ).toBeDefined();
  window.location.hash = "#/instructions";
  expect(await screen.findByText("Read the claim.")).toBeDefined();
  expect(
    screen
      .getByRole("link", { name: "Instructions" })
      .getAttribute("aria-current"),
  ).toBe("page");
});
