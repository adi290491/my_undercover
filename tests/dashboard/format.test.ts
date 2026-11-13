import { expect, it } from "vitest";
import {
  date,
  dateRange,
  label,
  money,
  statusLabel,
} from "../../dashboard/src/format";
import { parse } from "../../dashboard/src/router";

it("writes money in US dollars", () => {
  expect(money(1250)).toBe("$1,250.00");
  expect(money(0)).toBe("$0.00");
  expect(money(80.5)).toBe("$80.50");
});

it("writes dates as month, day and year", () => {
  expect(date("2026-06-24")).toBe("Jun 24, 2026");
  expect(date("2026-01-01")).toBe("Jan 1, 2026");
});

it("turns codes into labels", () => {
  expect(label("trip_delay")).toBe("Trip delay");
  expect(label("emergency_medical")).toBe("Emergency medical");
  expect(label("baggage")).toBe("Baggage");
  expect(statusLabel("awaiting_signoff")).toBe("Awaiting sign-off");
  expect(statusLabel("in_progress")).toBe("In progress");
});

it("reads the page from the address", () => {
  expect(parse("")).toEqual({ page: "queue" });
  expect(parse("#/")).toEqual({ page: "queue" });
  expect(parse("#/claims/CLM-1001")).toEqual({
    page: "claim",
    claimId: "CLM-1001",
  });
  expect(parse("#/instructions")).toEqual({ page: "instructions" });
  expect(parse("#/claims/")).toEqual({ page: "missing" });
  expect(parse("#/somewhere")).toEqual({ page: "missing" });
});

it("writes date ranges", () => {
  expect(dateRange("2026-06-10", "2026-06-18")).toBe("Jun 10 to Jun 18, 2026");
  expect(dateRange("2026-12-28", "2027-01-04")).toBe(
    "Dec 28, 2026 to Jan 4, 2027",
  );
});
