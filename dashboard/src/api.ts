export type Status = "waiting" | "in_progress" | "awaiting_signoff" | "decided";

export const STATUSES: Status[] = [
  "waiting",
  "in_progress",
  "awaiting_signoff",
  "decided",
];

export interface ClaimSummary {
  claim_id: string;
  claim_type: string;
  customer_name: string;
  amount_claimed: number;
  submitted_on: string;
  status: Status;
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
