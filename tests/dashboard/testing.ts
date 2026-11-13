import { cleanup } from "@testing-library/react";
import { afterEach, vi } from "vitest";
import type { ClaimSummary } from "../../dashboard/src/api";

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
    ...overrides,
  };
}
