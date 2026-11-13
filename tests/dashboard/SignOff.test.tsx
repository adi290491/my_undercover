import { fireEvent, render, screen, within } from "@testing-library/react";
import { expect, it } from "vitest";
import type { Claim, Handler } from "../../dashboard/src/api";
import { ClaimPage } from "../../dashboard/src/ClaimPage";
import { claim, claimRoutes, decision, Refusal, stubApi } from "./testing";

const handlers: Handler[] = [
  ["HND-01", "Dana Whitfield", "Senior Claims Handler"],
  ["HND-02", "Marcus Oyelaran", "Claims Handler"],
  ["HND-03", "Priya Raman", "Claims Handler"],
].map(([handler_id = "", name = "", role = ""]) => ({
  handler_id,
  name,
  role,
  can_approve_over_limit: true,
}));

const waiting = claim({
  status: "awaiting_signoff",
  thread_id: "thread-1",
  decision: decision({ payout: 1150 }),
});

async function panel() {
  return within(
    await screen.findByRole("region", { name: "Sign off the payout" }),
  );
}

it("signs off a payout as a handler, which pays it", async () => {
  let current: Claim = waiting;
  const calls = stubApi({
    ...claimRoutes(),
    "/api/claims/CLM-1001": () => current,
    "/api/handlers": handlers,
    "POST /api/claims/CLM-1001/sign-off": () => {
      current = {
        ...waiting,
        status: "decided",
        payment: { amount: 1150, paid_at: "2026-11-13T16:00:00+00:00" },
        sign_off: {
          handler_id: "HND-01",
          handler_name: "Dana Whitfield",
          signed_at: "2026-11-13T16:00:00+00:00",
        },
      };
      return current;
    },
  });
  render(<ClaimPage claimId="CLM-1001" />);
  const form = await panel();
  const button = form.getByRole("button", {
    name: "Sign off and pay $1,150.00",
  });
  expect(button.hasAttribute("disabled")).toBe(true);
  const picker = form.getByLabelText("Handler");
  expect(
    await form.findByRole("option", {
      name: "Dana Whitfield, Senior Claims Handler",
    }),
  ).toBeDefined();
  expect(form.getAllByRole("option").map((o) => o.textContent)).toEqual([
    "Choose a handler",
    "Dana Whitfield, Senior Claims Handler",
    "Marcus Oyelaran, Claims Handler",
    "Priya Raman, Claims Handler",
  ]);

  fireEvent.change(picker, { target: { value: "HND-01" } });
  expect(button.hasAttribute("disabled")).toBe(false);
  fireEvent.click(button);

  expect(await screen.findByText(/Dana Whitfield, Nov 13, 2026/)).toBeDefined();
  expect(
    screen.queryByRole("region", { name: "Sign off the payout" }),
  ).toBeNull();
  expect(screen.getByText("Decided", { selector: ".badge" })).toBeDefined();
  expect(calls.find((c) => c.method === "POST")?.body).toEqual({
    handler_id: "HND-01",
  });
});

it("only offers handlers who can sign off over the limit", async () => {
  stubApi({
    ...claimRoutes(),
    "/api/claims/CLM-1001": waiting,
    "/api/handlers": [
      ...handlers,
      {
        handler_id: "HND-04",
        name: "Sam Trainee",
        role: "Trainee",
        can_approve_over_limit: false,
      },
    ],
  });
  render(<ClaimPage claimId="CLM-1001" />);
  const form = await panel();
  await form.findByRole("option", { name: "Priya Raman, Claims Handler" });
  expect(form.queryByRole("option", { name: /Sam Trainee/ })).toBeNull();
});

it("shows a refused sign-off", async () => {
  stubApi({
    ...claimRoutes(),
    "/api/claims/CLM-1001": waiting,
    "/api/handlers": handlers,
    "POST /api/claims/CLM-1001/sign-off": new Refusal(
      409,
      "CLM-1001 is decided, so it can't be signed off.",
    ),
  });
  render(<ClaimPage claimId="CLM-1001" />);
  const form = await panel();
  await form.findByRole("option", { name: "Priya Raman, Claims Handler" });
  fireEvent.change(form.getByLabelText("Handler"), {
    target: { value: "HND-03" },
  });
  fireEvent.click(
    form.getByRole("button", { name: "Sign off and pay $1,150.00" }),
  );
  expect(
    await form.findByText("CLM-1001 is decided, so it can't be signed off."),
  ).toBeDefined();
});

it("says when the handlers can't be loaded", async () => {
  stubApi({
    ...claimRoutes(),
    "/api/claims/CLM-1001": waiting,
    "/api/handlers": new Refusal(500, "The handlers are unavailable."),
  });
  render(<ClaimPage claimId="CLM-1001" />);
  const form = await panel();
  expect(await form.findByText("The handlers are unavailable.")).toBeDefined();
});
