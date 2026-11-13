import { cleanup } from "@testing-library/react";
import { afterEach, vi } from "vitest";
import type {
  Claim,
  ClaimSummary,
  Decision,
  PastClaim,
  Policy,
  Step,
} from "../../dashboard/src/api";

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  vi.useRealTimers();
  window.location.hash = "";
});

export interface Call {
  method: string;
  path: string;
  body: unknown;
}

export class Refusal {
  constructor(
    readonly status: number,
    readonly detail: unknown,
  ) {}
}

function respond(reply: unknown): Response {
  if (reply instanceof Refusal) {
    return new Response(JSON.stringify({ detail: reply.detail }), {
      status: reply.status,
    });
  }
  return new Response(JSON.stringify(reply));
}

export function stubApi(routes: Record<string, unknown>): Call[] {
  const calls: Call[] = [];
  vi.stubGlobal(
    "fetch",
    vi.fn((input: string, init?: RequestInit) => {
      const method = init?.method ?? "GET";
      const body =
        typeof init?.body === "string"
          ? (JSON.parse(init.body) as unknown)
          : undefined;
      calls.push({ method, path: input, body });
      const key = `${method} ${input}`;
      const reply = key in routes ? routes[key] : routes[input];
      if (reply === undefined) {
        return Promise.resolve(respond(new Refusal(404, `No stub for ${key}`)));
      }
      return Promise.resolve(
        respond(
          typeof reply === "function" ? (reply as () => unknown)() : reply,
        ),
      );
    }),
  );
  return calls;
}

export function summary(
  claimId: string,
  overrides: Partial<ClaimSummary> = {},
): ClaimSummary {
  return {
    claim_id: claimId,
    claim_type: "trip_delay",
    customer_name: "Maya Patel",
    amount_claimed: 420,
    submitted_on: "2026-06-24",
    status: "waiting",
    decision: null,
    payout: null,
    ...overrides,
  };
}

export function claim(overrides: Partial<Claim> = {}): Claim {
  return {
    claim_id: "CLM-1001",
    claim_type: "trip_delay",
    customer_name: "Maya Patel",
    amount_claimed: 420,
    submitted_on: "2026-06-24",
    status: "waiting",
    thread_id: null,
    decision: null,
    payment: null,
    sign_off: null,
    policy_id: "POL-2001",
    customer_id: "CUS-3001",
    incident_date: "2026-06-18",
    incident_location: "Rome, Italy",
    summary: "Flight home canceled by the airline, rebooked the next morning",
    story: "My flight home from Rome on June 18 was canceled by Meridian Air.",
    items: [
      {
        description: "Airport hotel, one night",
        category: "accommodation",
        amount: 245,
      },
      { description: "Dinner and breakfast", category: "meals", amount: 95 },
      {
        description: "Taxis between the airport and the hotel",
        category: "transport",
        amount: 80,
      },
    ],
    documents: [
      {
        name: "Meridian Air cancellation notice",
        type: "carrier_report",
        content: "Flight MA 611 was canceled because of crew availability.",
      },
      {
        name: "Hotel receipt",
        type: "receipt",
        content: "One night. Total paid: $245.00.",
      },
    ],
    ...overrides,
  };
}

export const policy: Policy = {
  policy_id: "POL-2001",
  customer_id: "CUS-3001",
  plan: "premium",
  add_ons: [],
  purchased_on: "2026-04-22",
  sold_through: "Meridian Air checkout",
  trip: {
    destination: "Rome, Italy",
    departs_on: "2026-06-10",
    returns_on: "2026-06-18",
    trip_cost: 3100,
  },
  travelers: ["Maya Patel"],
  status: "active",
};

export const history: PastClaim[] = [
  {
    claim_id: "CLM-0412",
    filed_on: "2024-08-19",
    incident_date: "2024-08-09",
    claim_type: "baggage_delay",
    summary: "Checked bag arrived 30 hours late in Lisbon",
    outcome: "approved",
    amount_paid: 140,
  },
];

export function claimRoutes(
  overrides: Partial<Claim> = {},
): Record<string, unknown> {
  return {
    "/api/claims/CLM-1001": claim(overrides),
    "/api/policies/POL-2001": policy,
    "/api/customers/CUS-3001/claims": history,
    "/api/claims/CLM-1001/steps": [],
  };
}

export function decision(overrides: Partial<Decision> = {}): Decision {
  return {
    decision: "approve",
    payout: 420,
    reason:
      "The flight was canceled for a crew problem. The hotel, meals and taxis are covered.",
    policy_section: {
      number: 3,
      title: "Trip Delay",
      text: "We pay when your carrier delays you for at least your plan's waiting period.",
    },
    decided_at: "2026-11-13T15:04:05+00:00",
    ...overrides,
  };
}

export function step(
  stepId: number,
  kind: Step["kind"],
  text: string,
  threadId = "thread-1",
): Step {
  return {
    step_id: stepId,
    claim_id: "CLM-1001",
    thread_id: threadId,
    kind,
    text,
    created_at: "2026-11-13T15:04:05+00:00",
  };
}
