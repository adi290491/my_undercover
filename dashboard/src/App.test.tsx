import { act, cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { App } from "./App";
import { date, money, words } from "./format";
import { parse } from "./router";
import { claim, claimRoutes, stubApi, summary } from "./testing";

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  window.location.hash = "";
});

describe("routing", () => {
  it("parses each page", () => {
    expect(parse("")).toEqual({ page: "queue" });
    expect(parse("#/claims/CLM-1001")).toEqual({
      page: "claim",
      claimId: "CLM-1001",
    });
    expect(parse("#/instructions")).toEqual({ page: "instructions" });
    expect(parse("#/nowhere")).toEqual({ page: "queue" });
  });

  it("follows the hash between pages", async () => {
    stubApi({
      "GET /api/claims": [summary],
      "GET /api/instructions": { instructions: "Decide claims." },
      ...claimRoutes(claim),
    });
    render(<App />);
    expect(
      await screen.findByRole("heading", { name: "Claims queue" }),
    ).toBeDefined();
    act(() => {
      window.location.hash = "#/instructions";
      window.dispatchEvent(new HashChangeEvent("hashchange"));
    });
    expect(await screen.findByText("Decide claims.")).toBeDefined();
    act(() => {
      window.location.hash = "#/claims/CLM-1001";
      window.dispatchEvent(new HashChangeEvent("hashchange"));
    });
    expect(
      await screen.findByText("My flight home from Rome was canceled."),
    ).toBeDefined();
  });
});

describe("formatting", () => {
  it("shows money in US dollars", () => {
    expect(money(1250)).toBe("$1,250.00");
  });

  it("shows dates without shifting the day", () => {
    expect(date("2026-06-24")).toBe("Jun 24, 2026");
  });

  it("turns codes into words", () => {
    expect(words("trip_delay")).toBe("Trip delay");
  });
});
