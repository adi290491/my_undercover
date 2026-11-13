export type Status = "waiting" | "in_progress" | "awaiting_signoff" | "decided";

export const STATUSES: Status[] = [
  "waiting",
  "in_progress",
  "awaiting_signoff",
  "decided",
];

export type Outcome = "approve" | "decline" | "refer";

export type StepKind = "tool_call" | "tool_result" | "message" | "error";

interface ClaimBase {
  claim_id: string;
  claim_type: string;
  customer_name: string;
  amount_claimed: number;
  submitted_on: string;
  status: Status;
}

export interface ClaimSummary extends ClaimBase {
  decision: Outcome | null;
  payout: number | null;
}

export interface Section {
  number: number;
  title: string;
  text: string;
}

export interface Decision {
  decision: Outcome;
  payout: number;
  reason: string;
  policy_section: Section;
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

export interface Step {
  step_id: number;
  claim_id: string;
  thread_id: string;
  kind: StepKind;
  text: string;
  created_at: string;
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

export interface Claim extends ClaimBase {
  thread_id: string | null;
  decision: Decision | null;
  payment: Payment | null;
  sign_off: SignOff | null;
  policy_id: string;
  customer_id: string;
  incident_date: string;
  incident_location: string;
  summary: string;
  story: string;
  items: Item[];
  documents: ClaimDocument[];
}

export interface Policy {
  policy_id: string;
  customer_id: string;
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
  status: string;
}

export interface PastClaim {
  claim_id: string;
  filed_on: string;
  incident_date: string;
  claim_type: string;
  summary: string;
  outcome: string;
  amount_paid: number;
}

export interface Handler {
  handler_id: string;
  name: string;
  role: string;
  can_approve_over_limit: boolean;
}

export interface Text {
  text: string;
}

async function read<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const body = (await response.json()) as { detail?: unknown };
    throw new Error(
      typeof body.detail === "string"
        ? body.detail
        : `The request failed with status ${String(response.status)}.`,
    );
  }
  return (await response.json()) as T;
}

export async function getJson<T>(path: string): Promise<T> {
  return read<T>(await fetch(path));
}

export async function postJson<T>(path: string, body: unknown): Promise<T> {
  return read<T>(
    await fetch(path, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),
  );
}
