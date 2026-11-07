import { useCallback, useEffect, useState } from "react";

export type Status = "waiting" | "in_progress" | "awaiting_signoff" | "decided";

export interface ClaimSummary {
  claim_id: string;
  claim_type: string;
  customer_name: string;
  amount_claimed: number;
  submitted_on: string;
  summary: string;
  status: Status;
}

export interface Item {
  description: string;
  category: string;
  amount: number;
}

export interface ClaimDocument {
  name: string;
  type: string;
  content: string;
}

export interface Decision {
  decision: "approve" | "decline" | "refer";
  payout: number;
  reason: string;
  policy_section: string;
  decided_at: string;
}

export interface Payment {
  amount: number;
  paid_at: string;
}

export interface SignOff {
  handler_id: string;
  handler_name: string;
  signed_at: string;
}

export interface Claim extends ClaimSummary {
  policy_id: string;
  customer_id: string;
  incident_date: string;
  incident_location: string;
  story: string;
  items: Item[];
  documents: ClaimDocument[];
  thread_id: string | null;
  decision: Decision | null;
  payment: Payment | null;
  sign_off: SignOff | null;
}

export interface Policy {
  policy_id: string;
  plan: string;
  add_ons: string[];
  purchased_on: string;
  sold_through: string;
  trip: {
    destination: string;
    departs_on: string;
    returns_on: string;
    trip_cost: number;
  };
  travelers: string[];
}

export interface PastClaim {
  claim_id: string;
  filed_on: string;
  claim_type: string;
  summary: string;
  outcome: string;
  amount_paid: number;
}

export interface ClaimHistory {
  customer_since: string;
  previous_claims: PastClaim[];
}

export interface Handler {
  handler_id: string;
  name: string;
  role: string;
}

export interface Step {
  step_id: number;
  at: string;
  kind: "tool_call" | "tool_result" | "message" | "error";
  text: string;
}

async function read<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const body = (await response.json()) as { detail?: unknown };
    throw new Error(
      typeof body.detail === "string" ? body.detail : response.statusText,
    );
  }
  return (await response.json()) as T;
}

export async function get<T>(path: string): Promise<T> {
  return read<T>(await fetch(path));
}

export async function post<T>(path: string, body: object = {}): Promise<T> {
  const response = await fetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  return read<T>(response);
}

export interface Loaded<T> {
  data?: T;
  error?: string;
}

export function useApi<T>(path: string, version = 0): Loaded<T> {
  const [loaded, setLoaded] = useState<Loaded<T>>({});
  useEffect(() => {
    let live = true;
    get<T>(path).then(
      (data) => {
        if (live) setLoaded({ data });
      },
      (error: unknown) => {
        if (live) setLoaded({ error: String(error) });
      },
    );
    return () => {
      live = false;
    };
  }, [path, version]);
  return loaded;
}

export function useInterval(callback: () => void, ms: number | null) {
  useEffect(() => {
    if (ms === null) return;
    const id = setInterval(callback, ms);
    return () => {
      clearInterval(id);
    };
  }, [callback, ms]);
}

export function useVersion(): [number, () => void] {
  const [version, setVersion] = useState(0);
  const bump = useCallback(() => {
    setVersion((v) => v + 1);
  }, []);
  return [version, bump];
}
