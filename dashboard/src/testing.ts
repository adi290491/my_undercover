import { vi } from "vitest";
import type { Claim, ClaimHistory, ClaimSummary, Policy } from "./api";

export class Failure {
  constructor(
    readonly status: number,
    readonly detail: string,
  ) {}
}

export type Routes = Record<string, unknown>;

export function stubApi(routes: Routes) {
  const fetchMock = vi.fn((input: string, init?: RequestInit) => {
    const key = `${init?.method ?? "GET"} ${input}`;
    const reply = key in routes ? routes[key] : new Failure(404, `No ${key}`);
    const response =
      reply instanceof Failure
        ? new Response(JSON.stringify({ detail: reply.detail }), {
            status: reply.status,
          })
        : new Response(JSON.stringify(reply));
    return Promise.resolve(response);
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

export const summary: ClaimSummary = {
  claim_id: "CLM-1001",
  claim_type: "trip_delay",
  customer_name: "Maya Patel",
  amount_claimed: 1420,
  submitted_on: "2026-06-24",
  summary: "Flight home canceled by the airline",
  status: "waiting",
};

export const claim: Claim = {
  ...summary,
  policy_id: "POL-2001",
  customer_id: "CUS-3001",
  incident_date: "2026-06-18",
  incident_location: "Rome, Italy",
  story: "My flight home from Rome was canceled.",
  items: [
    { description: "Airport hotel", category: "accommodation", amount: 1245 },
    { description: "Taxis", category: "transport", amount: 175 },
  ],
  documents: [
    {
      name: "Hotel receipt",
      type: "receipt",
      content: "Hotel Aurelia, one night.",
    },
  ],
  thread_id: null,
  decision: null,
  payment: null,
  sign_off: null,
};

export const policy: Policy = {
  policy_id: "POL-2001",
  plan: "premium",
  add_ons: ["electronics_plus"],
  purchased_on: "2026-04-22",
  sold_through: "Meridian Air checkout",
  trip: {
    destination: "Rome, Italy",
    departs_on: "2026-06-10",
    returns_on: "2026-06-18",
    trip_cost: 3100,
  },
  travelers: ["Maya Patel"],
};

export const history: ClaimHistory = {
  customer_since: "2023-04-11",
  previous_claims: [
    {
      claim_id: "CLM-0412",
      filed_on: "2024-08-19",
      claim_type: "baggage_delay",
      summary: "Checked bag arrived 30 hours late",
      outcome: "approved",
      amount_paid: 140,
    },
  ],
};

export function claimRoutes(current: Claim): Routes {
  return {
    "GET /api/claims/CLM-1001": current,
    "GET /api/policies/POL-2001": policy,
    "GET /api/customers/CUS-3001/claims": history,
    "GET /api/claims/CLM-1001/steps": [],
    "GET /api/handlers": [],
  };
}
